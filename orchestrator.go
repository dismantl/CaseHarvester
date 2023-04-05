package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/akamensky/argparse"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/cloudwatch"
	cwtypes "github.com/aws/aws-sdk-go-v2/service/cloudwatch/types"
	"github.com/aws/aws-sdk-go-v2/service/cloudwatchlogs"
	"github.com/aws/aws-sdk-go-v2/service/ec2"
	ec2types "github.com/aws/aws-sdk-go-v2/service/ec2/types"
	"github.com/aws/aws-sdk-go-v2/service/eventbridge"
	"github.com/aws/aws-sdk-go-v2/service/ssm"
	"github.com/gorilla/mux"
	"github.com/lzap/cloudwatchwriter2"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"github.com/rs/zerolog/pkgerrors"
	"github.com/spf13/viper"
)

const (
	MaxRetryAttempts                 = 5
	RebootTimerDuration              = 5 * time.Minute
	CheckCountTimerDuration          = 15 * time.Second
	RefreshInstanceDataTimerDuration = 5 * time.Minute
	CollectMetricsTimerDuration      = time.Second
	ReportMetricsTimerDuration       = time.Minute
	NotifierRuleNameSetting          = "notifier_rule_name"
	CountParameterNameSetting        = "%s_count_parameter_name"
	LaunchTemplateIdSetting          = "%s_launch_template_id"
	QueueNotEmptyAlarmNameSetting    = "%s_queue_not_empty_alarm_name"
	CloudwatchMetricsNamespace       = "CaseHarvester"
	CloudwatchLogGroupName           = "caseharvester_orchestrator"
)

type Component string

const (
	SpiderComponent  Component = "spider"
	ScraperComponent Component = "scraper"
)

var AllComponents []Component = []Component{SpiderComponent, ScraperComponent}

type Orchestrator struct {
	environment string
	ec2Client   *ec2.Client
	ebClient    *eventbridge.Client
	ssmClient   *ssm.Client
	cwClient    *cloudwatch.Client
}

type InstanceState struct {
	instanceId  string
	component   Component
	state       ec2types.InstanceStateName
	rebootTimer *time.Timer
}

type InstanceUpdate struct {
	instanceId string
	state      ec2types.InstanceStateName
}

type QueueUpdate struct {
	component     Component
	queueHasItems bool
}

type Metric struct {
	component Component
	timestamp time.Time
	counts    map[ec2types.InstanceStateName]int
}

func NewOrchestrator(cfg aws.Config, environment string) *Orchestrator {
	return &Orchestrator{
		environment: environment,
		ec2Client:   ec2.NewFromConfig(cfg),
		ebClient:    eventbridge.NewFromConfig(cfg),
		ssmClient:   ssm.NewFromConfig(cfg),
		cwClient:    cloudwatch.NewFromConfig(cfg),
	}
}

func (orchestrator *Orchestrator) Start(done chan bool) {
	// State variables
	instances := make(map[string]*InstanceState)
	instanceIds := make(map[Component][]string)
	queueHasItems := make(map[Component]bool)
	metrics := make(map[Component][]Metric)

	updatesChan := make(chan []InstanceUpdate, 1000)
	queueUpdateChan := make(chan QueueUpdate)
	server := orchestrator.setupHttpHandlers(updatesChan, queueUpdateChan)

	// Recover from panics: log error and cleanup
	defer func() {
		if r := recover(); r != nil {
			log.Error().Err(fmt.Errorf("%v", r)).Msg("Caught panic")
			orchestrator.cleanup(instances, server)
		}
	}()

	// Check queue_not_empty_alarm states
	log.Info().Msg("Checking current alarm states")
	for _, component := range AllComponents {
		alarmName := viper.GetString(fmt.Sprintf(QueueNotEmptyAlarmNameSetting, component))
		response, err := orchestrator.cwClient.DescribeAlarms(context.TODO(), &cloudwatch.DescribeAlarmsInput{
			AlarmNames: []string{alarmName},
		})
		if err != nil {
			log.Fatal().Err(err).Msgf("Failed to get alarm state for %s", alarmName)
		}
		alarm := response.MetricAlarms[0]
		if alarm.StateValue == cwtypes.StateValueAlarm {
			queueHasItems[component] = true
		}
	}

	// Start HTTP server
	log.Info().Msg("Starting HTTP update handlers")
	go server.ListenAndServe()

	// Enable queue_not_empty_alarm actions and instance state change notification rule
	go orchestrator.enableTriggers()

	// Do initial check of desired instance counts so we can spin them up
	log.Info().Msg("Checking initial count parameters")
	newInstancesChan := make(chan []*InstanceState, 2)
	rebootChan := make(chan string)
	go orchestrator.checkCountParams(instanceIds, instances, newInstancesChan, rebootChan)

	// Set tickers
	collectTicker := time.NewTicker(CollectMetricsTimerDuration)
	reportTicker := time.NewTicker(ReportMetricsTimerDuration)
	checkCountTicker := time.NewTicker(CheckCountTimerDuration)
	refreshTicker := time.NewTicker(RefreshInstanceDataTimerDuration)

	// Main event loop
	metricsChan := make(chan []Metric)
	for {
		select {
		case update := <-queueUpdateChan:
			if update.queueHasItems {
				log.Info().Msgf("%s queue has items available", strings.Title(string(update.component)))
			} else {
				log.Info().Msgf("%s queue is empty", strings.Title(string(update.component)))
			}
			queueHasItems[update.component] = update.queueHasItems
		case newInstances := <-newInstancesChan:
			for _, instance := range newInstances {
				instances[instance.instanceId] = instance
				instanceIds[instance.component] = append(instanceIds[instance.component], instance.instanceId)
			}
		case instanceId := <-rebootChan:
			instance := instances[instanceId]
			if instance.state == ec2types.InstanceStateNamePending || instance.state == ec2types.InstanceStateNameRunning {
				log.Info().Str("instanceId", instanceId).Msg("Reboot timer triggered, stopping instance")
				go orchestrator.stopInstance(instanceId)
			}
		case updates := <-updatesChan:
			for _, update := range updates {
				instance, present := instances[update.instanceId]
				if present {
					instance.state = update.state
					log.Debug().Str("instanceId", instance.instanceId).Str("state", string(update.state)).Send()

					// Start instance if stopped and queue not empty
					if update.state == ec2types.InstanceStateNameStopped && queueHasItems[instance.component] {
						log.Info().Str("instanceId", instance.instanceId).Msg("Starting instance")
						go orchestrator.startInstance(instance.instanceId)

						// Set new reboot timer
						instance.rebootTimer.Stop()
						instance.rebootTimer = time.AfterFunc(RebootTimerDuration, func() {
							rebootChan <- instance.instanceId
						})
					} else if update.state == ec2types.InstanceStateNameTerminated {
						// Remove terminated instances
						log.Info().Str("instanceId", instance.instanceId).Msg("Removing terminated instance")
						for i, instanceId := range instanceIds[instance.component] {
							if instanceId == instance.instanceId {
								instanceIds[instance.component] = append(
									instanceIds[instance.component][:i],
									instanceIds[instance.component][i+1:]...,
								)
							}
						}
						instance.rebootTimer.Stop()
						delete(instances, instance.instanceId)
					}
				}
			}
		case newMetrics := <-metricsChan:
			for _, metric := range newMetrics {
				metrics[metric.component] = append(metrics[metric.component], metric)
			}
		case <-checkCountTicker.C:
			// log.Debug().Msg("Checking orchestrator count parameters")
			go orchestrator.checkCountParams(instanceIds, instances, newInstancesChan, rebootChan)
		case <-refreshTicker.C:
			log.Debug().Msg("Refreshing instance data")
			go orchestrator.refreshInstanceData(instances, updatesChan)
		case <-collectTicker.C:
			go orchestrator.collectMetrics(instanceIds, instances, metricsChan)
		case <-reportTicker.C:
			log.Debug().Msgf("Reporting %d metrics", len(metrics[SpiderComponent])+len(metrics[ScraperComponent]))
			go orchestrator.reportMetrics(metrics)
			metrics = make(map[Component][]Metric)
		case <-done:
			log.Info().Msg("Received signal to shut down orchestrator")
			orchestrator.cleanup(instances, server)
			done <- true
			return
		}
	}
}

func (orchestrator *Orchestrator) reportMetrics(metrics map[Component][]Metric) {
	var dat []cwtypes.MetricDatum
	for component, metrics := range metrics {
		dimensions := []cwtypes.Dimension{
			{
				Name:  aws.String("Environment"),
				Value: aws.String(orchestrator.environment),
			},
			{
				Name:  aws.String("Component"),
				Value: aws.String(string(component)),
			},
		}
		for _, metric := range metrics {
			for _, state := range []ec2types.InstanceStateName{
				ec2types.InstanceStateNamePending,
				ec2types.InstanceStateNameRunning,
				ec2types.InstanceStateNameStopping,
				ec2types.InstanceStateNameStopped,
				ec2types.InstanceStateNameShuttingDown,
				ec2types.InstanceStateNameTerminated,
			} {
				dat = append(dat, cwtypes.MetricDatum{
					MetricName:        aws.String(fmt.Sprintf("%sInstances", strings.Title(string(state)))),
					Dimensions:        dimensions,
					Timestamp:         aws.Time(metric.timestamp),
					Value:             aws.Float64(float64(metric.counts[state])),
					StorageResolution: aws.Int32(1),
				})
			}
		}
	}
	_, err := orchestrator.cwClient.PutMetricData(context.TODO(), &cloudwatch.PutMetricDataInput{
		MetricData: dat,
		Namespace:  aws.String(CloudwatchMetricsNamespace),
	})
	if err != nil {
		log.Error().Err(err).Msg("Failed to report metrics")
	}
}

func (orchestrator *Orchestrator) collectMetrics(
	instanceIds map[Component][]string,
	instances map[string]*InstanceState,
	metricsChan chan<- []Metric,
) {
	// Round to the nearest second
	metricTime := time.Now().Round(time.Second)
	var metrics []Metric
	for _, component := range AllComponents {
		metric := Metric{
			component: component,
			timestamp: metricTime,
			counts:    make(map[ec2types.InstanceStateName]int),
		}
		for _, instanceId := range instanceIds[component] {
			metric.counts[instances[instanceId].state] += 1
		}
		metrics = append(metrics, metric)
	}
	metricsChan <- metrics
}

func (orchestrator *Orchestrator) enableTriggers() {
	// Enable queue_not_empty_alarm actions to notify us whether queue has items or not
	for _, component := range AllComponents {
		alarmName := viper.GetString(fmt.Sprintf(QueueNotEmptyAlarmNameSetting, component))
		log.Info().Msgf("Enabling alarm actions for %s", alarmName)
		_, err := orchestrator.cwClient.EnableAlarmActions(context.TODO(), &cloudwatch.EnableAlarmActionsInput{
			AlarmNames: []string{alarmName},
		})
		if err != nil {
			log.Fatal().Err(err).Msgf("Failed to enable alarm actions for %s", alarmName)
		}
	}

	// Enable eventbridge rule to notify us of EC2 instance state changes
	ruleName := viper.GetString(NotifierRuleNameSetting)
	if ruleName == "" {
		log.Fatal().Msgf("Cannot find setting %s", NotifierRuleNameSetting)
	}
	log.Info().Msgf("Enabling EventBridge rule %s", ruleName)
	_, err := orchestrator.ebClient.EnableRule(context.TODO(), &eventbridge.EnableRuleInput{
		Name: aws.String(ruleName),
	})
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to enable EventBridge rule")
	}
}

func (orchestrator *Orchestrator) cleanup(instances map[string]*InstanceState, server *http.Server) {
	var instanceIds []string
	for instanceId := range instances {
		instanceIds = append(instanceIds, instanceId)
	}

	// Terminate all instances
	log.Info().Msgf("Terminating %d instances", len(instanceIds))
	_, err := orchestrator.ec2Client.TerminateInstances(context.TODO(), &ec2.TerminateInstancesInput{
		InstanceIds: instanceIds,
	})
	if err != nil {
		log.Error().Err(err).Msg("Error terminating instances")
	}

	// Disable eventbridge rule
	ruleName := viper.GetString(NotifierRuleNameSetting)
	log.Info().Msgf("Disabling EventBridge rule %s", ruleName)
	_, err = orchestrator.ebClient.DisableRule(context.TODO(), &eventbridge.DisableRuleInput{
		Name: aws.String(ruleName),
	})
	if err != nil {
		log.Error().Err(err).Msg("Error disabling EventBridge rule")
	}

	// Disable queue_not_empty_alarm actions
	for _, component := range AllComponents {
		alarmName := viper.GetString(fmt.Sprintf(QueueNotEmptyAlarmNameSetting, component))
		log.Info().Msgf("Disabling alarm actions for %s", alarmName)
		_, err := orchestrator.cwClient.DisableAlarmActions(context.TODO(), &cloudwatch.DisableAlarmActionsInput{
			AlarmNames: []string{alarmName},
		})
		if err != nil {
			log.Error().Err(err).Msgf("Error disabling alarm actions for %s", alarmName)
		}
	}

	// Shutdown http server
	log.Info().Msg("Shutting down HTTP server")
	if err := server.Shutdown(context.TODO()); err != nil {
		log.Error().Err(err).Msg("Error shutting down HTTP server")
	}
}

func (orchestrator *Orchestrator) checkCountParams(
	instanceIds map[Component][]string,
	instances map[string]*InstanceState,
	newInstancesChan chan<- []*InstanceState,
	rebootChan chan<- string,
) {
	for _, component := range AllComponents {
		countParamName := viper.GetString(fmt.Sprintf(CountParameterNameSetting, component))
		response, err := orchestrator.ssmClient.GetParameter(context.TODO(), &ssm.GetParameterInput{
			Name: aws.String(countParamName),
		})
		if err != nil {
			log.Error().Err(err).Msgf("Failed to get %s count parameter", component)
			continue
		}

		valStr := aws.ToString(response.Parameter.Value)
		count, err := strconv.Atoi(valStr)
		if err != nil {
			log.Error().Err(err).Msgf("Invalid count parameter for %s: %s", component, valStr)
			continue
		}

		diff := count - len(instanceIds[component])
		if diff > 0 {
			log.Info().Msgf("Launching %d %s instances", diff, component)
			launchTemplateId := viper.GetString(fmt.Sprintf(LaunchTemplateIdSetting, component))
			go orchestrator.launchInstances(component, launchTemplateId, diff, newInstancesChan, rebootChan)
		} else if diff < 0 {
			log.Info().Msgf("Terminating %d %s instances", -diff, component)
			go orchestrator.terminateInstances(instances, component, -diff)
		}
	}
}

func (orchestrator *Orchestrator) launchInstances(
	component Component,
	launchTemplateId string,
	count int,
	newInstancesChan chan<- []*InstanceState,
	rebootChan chan<- string,
) {
	tags := []ec2types.Tag{
		{
			Key:   aws.String("Name"),
			Value: aws.String(fmt.Sprintf("Case Harvester %s worker", component)),
		},
	}
	response, err := orchestrator.ec2Client.RunInstances(context.TODO(), &ec2.RunInstancesInput{
		MaxCount: aws.Int32(int32(count)),
		MinCount: aws.Int32(int32(count)),
		LaunchTemplate: &ec2types.LaunchTemplateSpecification{
			LaunchTemplateId: aws.String(launchTemplateId),
			Version:          aws.String("$Latest"),
		},
		TagSpecifications: []ec2types.TagSpecification{
			{
				ResourceType: ec2types.ResourceTypeInstance,
				Tags:         tags,
			},
			{
				ResourceType: ec2types.ResourceTypeVolume,
				Tags:         tags,
			},
			{
				ResourceType: ec2types.ResourceTypeNetworkInterface,
				Tags:         tags,
			},
		},
	})
	if err != nil {
		log.Error().Err(err).Msg("Failed to launch EC2 instances")
		return
	}
	var instances []*InstanceState
	for _, newInstance := range response.Instances {
		instanceId := aws.ToString(newInstance.InstanceId)
		log.Debug().Str("instanceId", instanceId).Str("state", string(newInstance.State.Name)).Msg("Launched instance")
		instance := &InstanceState{
			instanceId: instanceId,
			component:  component,
			state:      newInstance.State.Name,
			rebootTimer: time.AfterFunc(RebootTimerDuration, func() {
				rebootChan <- instanceId
			}),
		}
		instances = append(instances, instance)
	}
	newInstancesChan <- instances
}

func (orchestrator *Orchestrator) terminateInstances(instances map[string]*InstanceState, component Component, count int) {
	var toTerminate []string
	for _, instance := range instances {
		if len(toTerminate) < count && instance.component == component {
			toTerminate = append(toTerminate, instance.instanceId)
		}
	}
	if len(toTerminate) < count {
		log.Warn().Msgf(
			"Number of available %s instances (%d) less than requested to terminate (%d).",
			component, len(toTerminate), count)
	}

	_, err := orchestrator.ec2Client.TerminateInstances(context.TODO(), &ec2.TerminateInstancesInput{
		InstanceIds: toTerminate,
	})
	if err != nil {
		log.Error().Err(err).Msg("Failed to terminate instances")
	}
}

func (orchestrator *Orchestrator) refreshInstanceData(instances map[string]*InstanceState, updatesChan chan<- []InstanceUpdate) {
	var instanceIds []string
	for instanceId := range instances {
		instanceIds = append(instanceIds, instanceId)
	}
	paginator := ec2.NewDescribeInstancesPaginator(orchestrator.ec2Client, &ec2.DescribeInstancesInput{
		InstanceIds: instanceIds,
	})
	var updates []InstanceUpdate
	for paginator.HasMorePages() {
		response, err := paginator.NextPage(context.TODO())
		if err != nil {
			log.Error().Err(err).Msg("Failed to get instance data")
			return
		}
		for _, res := range response.Reservations {
			for _, instance := range res.Instances {
				updates = append(updates, InstanceUpdate{
					instanceId: aws.ToString(instance.InstanceId),
					state:      instance.State.Name,
				})
			}
		}
	}
	updatesChan <- updates
}

func (orchestrator *Orchestrator) startInstance(instanceId string) {
	response, err := orchestrator.ec2Client.StartInstances(context.TODO(), &ec2.StartInstancesInput{
		InstanceIds: []string{instanceId},
	})
	if err != nil {
		log.Error().Err(err).Str("instanceId", instanceId).Msg("Failed to start instance")
		return
	}
	if response.StartingInstances[0].CurrentState.Name != ec2types.InstanceStateNamePending {
		log.Warn().Str("instanceId", instanceId).Msgf(
			"Instance not in expected pending state: %s", response.StartingInstances[0].CurrentState.Name)
	}
}

func (orchestrator *Orchestrator) stopInstance(instanceId string) {
	_, err := orchestrator.ec2Client.StopInstances(context.TODO(), &ec2.StopInstancesInput{
		InstanceIds: []string{instanceId},
	})
	if err != nil {
		log.Error().Err(err).Str("instanceId", instanceId).Msg("Failed to stop instance")
	}
}

func (orchestrator *Orchestrator) setupHttpHandlers(
	updatesChan chan<- []InstanceUpdate,
	queueUpdateChan chan<- QueueUpdate,
) *http.Server {
	router := mux.NewRouter()
	for _, state := range []ec2types.InstanceStateName{
		ec2types.InstanceStateNamePending,
		ec2types.InstanceStateNameRunning,
		ec2types.InstanceStateNameStopping,
		ec2types.InstanceStateNameStopped,
		ec2types.InstanceStateNameShuttingDown,
		ec2types.InstanceStateNameTerminated,
	} {
		router.HandleFunc(fmt.Sprintf("/%s/{instance_id}", state), func(state ec2types.InstanceStateName) func(w http.ResponseWriter, r *http.Request) {
			return func(w http.ResponseWriter, r *http.Request) {
				updatesChan <- []InstanceUpdate{{
					instanceId: mux.Vars(r)["instance_id"],
					state:      state,
				}}
			}
		}(state))
	}
	for _, component := range AllComponents {
		router.HandleFunc(fmt.Sprintf("/%s/empty", component), func(component Component) func(w http.ResponseWriter, r *http.Request) {
			return func(w http.ResponseWriter, r *http.Request) {
				queueUpdateChan <- QueueUpdate{
					component:     component,
					queueHasItems: false,
				}
			}
		}(component))
		router.HandleFunc(fmt.Sprintf("/%s/available", component), func(component Component) func(w http.ResponseWriter, r *http.Request) {
			return func(w http.ResponseWriter, r *http.Request) {
				queueUpdateChan <- QueueUpdate{
					component:     component,
					queueHasItems: true,
				}
			}
		}(component))
	}
	return &http.Server{Addr: "0.0.0.0:80", Handler: router}
}

func main() {
	zerolog.ErrorStackMarshaler = pkgerrors.MarshalStack
	log.Logger = log.Output(
		zerolog.ConsoleWriter{Out: os.Stdout},
	).With().Timestamp().Logger().With().Caller().Logger()

	parser := argparse.NewParser("orchestrator",
		"Orchestrate Case Harvester spider and scraper EC2 instances")
	environment := parser.Selector("e", "environment",
		[]string{"production", "development"}, &argparse.Options{
			Required: true,
		})
	cloudwatch := parser.Flag("", "cloudwatch", &argparse.Options{
		Help: "Log to Cloudwatch",
	})
	if err := parser.Parse(os.Args); err != nil {
		log.Fatal().Msg(parser.Usage(err))
	}

	// Load config
	log.Info().Msg("Loading configuration")
	cwd, err := os.Getwd()
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to get CWD")
	}
	viper.SetConfigName(*environment)
	viper.SetConfigType("env")
	viper.AddConfigPath(filepath.Join(cwd, "env"))
	if err := viper.ReadInConfig(); err != nil {
		log.Fatal().Err(err).Msg("Error reading config: %w")
	}
	cfg, err := config.LoadDefaultConfig(context.TODO(),
		config.WithRegion("us-east-1"),
		config.WithRetryMaxAttempts(MaxRetryAttempts),
	)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to load default AWS config")
	}

	if *cloudwatch {
		cwClient := cloudwatchlogs.NewFromConfig(cfg)
		cloudwatchWriter, err := cloudwatchwriter2.NewWithClient(
			cwClient,
			time.Second,
			CloudwatchLogGroupName,
			time.Now().GoString(),
		)
		if err != nil {
			log.Fatal().Err(err).Msg("Failed to create Cloudwatch writer")
		}
		log.Logger = zerolog.New(zerolog.MultiLevelWriter(
			cloudwatchWriter,
			zerolog.ConsoleWriter{Out: os.Stdout}),
		).With().Timestamp().Logger().With().Caller().Logger()
	}

	orchestrator := NewOrchestrator(cfg, *environment)

	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)
	done := make(chan bool)
	go orchestrator.Start(done)
	<-sigs
	done <- true
	<-done
}
