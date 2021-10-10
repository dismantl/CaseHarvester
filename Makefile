CODE_SRC=src
PACKAGE_DIR=pkg
LIB_DIR=lib
DOCS_DIR=docs
ENV_DIR=env
SPIDER_DEPS=$(addprefix $(CODE_SRC)/,case_harvester.py \
	$(addprefix mjcs/,__init__.py spider.py config.py util.py session.py models/*.py))
SCRAPER_DEPS=$(addprefix $(CODE_SRC)/,case_harvester.py \
	$(addprefix mjcs/,__init__.py scraper.py config.py util.py session.py models/*.py))
PARSER_DEPS=$(addprefix $(CODE_SRC)/,parser/parser_lambda.py \
	$(addprefix mjcs/,__init__.py config.py util.py parser/*.py models/*.py))
SECRETS_FILE=secrets.json
STACK_PREFIX=caseharvester-stack
AWS_REGION=us-east-1
DB_NAME=mjcs
AWS_PROFILE=default
DOCKER_REPO_NAME=caseharvester

.PHONY: package package_parser deploy deploy_production \
	$(addprefix deploy_,static docker-repo spider scraper parser) \
	$(addsuffix _production,$(addprefix deploy_,static docker-repo spider scraper parser)) \
	test clean clean_all list_exports init init_production parser_notification \
	parser_notification_production docker_image docker_image_production sync docs \
	pause_scraper_service resume_scraper_service

define package_f
$(eval component = $(1))
mkdir -p $(PACKAGE_DIR)/$(component)
pip3 install -r $(CODE_SRC)/$(component)/requirements.txt -t $(PACKAGE_DIR)/$(component)/
cp $(CODE_SRC)/$(component)/$(component)_lambda.py $(PACKAGE_DIR)/$(component)/
cp -r $(CODE_SRC)/mjcs $(PACKAGE_DIR)/$(component)/
find $(PACKAGE_DIR) -name *.pyc -delete
find $(PACKAGE_DIR) -name __pycache__ -delete
rm -rf include
endef

define deploy_stack_f
$(eval component = $(1))
$(eval environment = $(2))
$(eval env_long = $(subst prod,production,$(subst dev,development,$(environment))))
$(eval include $(ENV_DIR)/base.env)
$(eval include $(ENV_DIR)/$(env_long).env)
aws cloudformation package --template-file cloudformation/stack-$(component).yaml \
	--output-template-file cloudformation/stack-$(component)-output.yaml \
	--s3-bucket $(STACK_PREFIX)-$(component)-$(environment)
aws cloudformation deploy --template-file cloudformation/stack-$(component)-output.yaml \
	--stack-name $(STACK_PREFIX)-$(component)-$(environment) \
	--capabilities CAPABILITY_IAM \
	--capabilities CAPABILITY_NAMED_IAM \
	--parameter-overrides \
		EnvironmentType=$(environment) DatabaseName=$(DB_NAME) \
		StaticStackName=$(STACK_PREFIX)-static-$(environment) \
		DockerRepoStackName=$(STACK_PREFIX)-docker-repo-$(environment) \
		ScraperStackName=$(STACK_PREFIX)-scraper-$(environment) \
		AWSRegion=$(AWS_REGION) \
		DockerRepoName=$(environment)_$(DOCKER_REPO_NAME) \
		UserAgent=$(USER_AGENT) \
		$(shell jq -r '.$(env_long) as $$x|$$x|keys[]|. + "=" + $$x[.]' $(SECRETS_FILE))
endef

define create_stack_bucket_f
$(eval component = $(1))
$(eval environment = $(2))
aws s3api create-bucket --bucket $(STACK_PREFIX)-$(component)-$(environment) --region $(AWS_REGION)
endef

define add_parser_notification_f
$(eval environment = $(1))
sleep 5 # so exports can propagate
aws cloudformation list-exports | awk '\
	/$(STACK_PREFIX)-static-$(environment)-CaseDetailsBucketName/ { getline; bucket=$$2 };\
	/$(STACK_PREFIX)-parser-$(environment)-ParserArn/ { getline; parser_arn=$$2 };\
	END { print bucket, parser_arn }' | \
	xargs printf "aws s3api put-bucket-notification-configuration --bucket %s \
	--notification-configuration \'{\"LambdaFunctionConfigurations\": \
	[{\"LambdaFunctionArn\":\"%s\",\"Events\":[\"s3:ObjectCreated:*\"]}]}\'" | bash
endef

define db_init_f
$(eval environment = $(1))
$(eval profile = $(or $(2),$(AWS_PROFILE),default))
DEV_MODE=1 python3 $(CODE_SRC)/case_harvester.py --environment $(environment) \
	--profile $(profile) db_init --db-name $(DB_NAME) --secrets-file $(SECRETS_FILE)
CASEHARVESTER_ENV=$(environment) alembic stamp head
endef

define create_docs_f
$(eval environment = $(1))
$(eval env_long = $(subst prod,production,$(subst dev,development,$(environment))))
aws cloudformation list-exports|grep \
	$(STACK_PREFIX)-static-$(environment)-DatabaseHostname -A1|grep Value|\
	awk '{print $$2}' | xargs \
	docker run -v "$(abspath $(DOCS_DIR)):/output" schemaspy/schemaspy:snapshot \
		-t pgsql \
		-db $(DB_NAME) \
		-s public \
		-u $(shell jq '.$(env_long).DatabaseUsername' $(SECRETS_FILE)) \
		-p $(shell jq '.$(env_long).DatabasePassword' $(SECRETS_FILE)) \
		-host
endef

define push_docker_image_f
$(eval environment = $(1))
$(shell aws ecr get-login --region $(AWS_REGION) --no-include-email)
$(eval REPO_NAME = $(environment)_$(DOCKER_REPO_NAME))
$(eval AWS_ACCOUNT_ID = $(shell aws sts get-caller-identity | grep Account | cut -d'"' -f4))
find $(CODE_SRC) -name *.pyc -delete
find $(CODE_SRC) -name __pycache__ -delete
docker build -t $(REPO_NAME) .
$(eval REPO_URL = $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(REPO_NAME))
docker tag $(REPO_NAME):latest $(REPO_URL):latest
docker push $(REPO_URL)
endef

define pause_scraper_service_f
$(eval environment = $(1))
aws application-autoscaling register-scalable-target --service-namespace ecs \
	--scalable-dimension ecs:service:DesiredCount --resource-id service/caseharvester_cluster_$(environment)/mjcs_scraper_service_$(environment) \
	--suspended-state '{"DynamicScalingInSuspended":true,"DynamicScalingOutSuspended":true,"ScheduledScalingSuspended":true}'
aws ecs update-service --cluster caseharvester_cluster_$(environment) --service mjcs_scraper_service_$(environment) \
	--desired-count 0
endef

define resume_scraper_service_f
$(eval environment = $(1))
aws application-autoscaling register-scalable-target --service-namespace ecs \
	--scalable-dimension ecs:service:DesiredCount --resource-id service/caseharvester_cluster_$(environment)/mjcs_scraper_service_$(environment) \
	--suspended-state '{"DynamicScalingInSuspended":false,"DynamicScalingOutSuspended":false,"ScheduledScalingSuspended":false}'
endef


.package-parser: $(PARSER_DEPS) $(CODE_SRC)/parser/requirements.txt
	$(call package_f,parser)
	cp -r $(LIB_DIR)/psycopg2 $(PACKAGE_DIR)/parser/
	touch $@

.create-stack-buckets:
	$(foreach env,dev prod,\
		$(foreach component,static docker-repo spider scraper parser,\
			$(call create_stack_bucket_f,$(component),$(env))\
		)\
	)
	touch $@

.deploy-static-dev: .create-stack-buckets cloudformation/stack-static.yaml $(SECRETS_FILE)
	$(call deploy_stack_f,static,dev)
	touch $@

.deploy-static-prod: .create-stack-buckets cloudformation/stack-static.yaml $(SECRETS_FILE)
	$(call deploy_stack_f,static,prod)
	touch $@

.deploy-docker-repo-dev: .create-stack-buckets .deploy-static-dev cloudformation/stack-docker-repo.yaml $(SECRETS_FILE)
	$(call deploy_stack_f,docker-repo,dev)
	touch $@

.deploy-docker-repo-prod: .create-stack-buckets .deploy-static-prod cloudformation/stack-docker-repo.yaml $(SECRETS_FILE)
	$(call deploy_stack_f,docker-repo,prod)
	touch $@

.push-docker-image-dev: .deploy-docker-repo-dev Dockerfile $(SPIDER_DEPS) $(SCRAPER_DEPS)
	$(call push_docker_image_f,dev)
	touch $@

.push-docker-image-prod: .deploy-docker-repo-prod Dockerfile $(SPIDER_DEPS) $(SCRAPER_DEPS)
	$(call push_docker_image_f,prod)
	touch $@

.deploy-spider-dev: .deploy-static-dev .deploy-scraper-dev cloudformation/stack-spider.yaml $(SECRETS_FILE)
	$(call deploy_stack_f,spider,dev)
	touch $@

.deploy-spider-prod: .deploy-static-prod .deploy-scraper-prod cloudformation/stack-spider.yaml $(SECRETS_FILE)
	$(call deploy_stack_f,spider,prod)
	touch $@

.deploy-scraper-dev: .deploy-static-dev cloudformation/stack-scraper.yaml $(SECRETS_FILE)
	$(call deploy_stack_f,scraper,dev)
	touch $@

.deploy-scraper-prod: .deploy-static-prod cloudformation/stack-scraper.yaml $(SECRETS_FILE)
	$(call deploy_stack_f,scraper,prod)
	touch $@

.deploy-parser-dev: .deploy-static-dev .package-parser cloudformation/stack-parser.yaml $(SECRETS_FILE)
	$(call deploy_stack_f,parser,dev)
	$(call add_parser_notification_f,dev)
	touch $@

.deploy-parser-prod: .deploy-static-prod .package-parser cloudformation/stack-parser.yaml $(SECRETS_FILE)
	$(call deploy_stack_f,parser,prod)
	$(call add_parser_notification_f,prod)
	touch $@

.init-dev: .deploy-static-dev .deploy-spider-dev .deploy-scraper-dev .deploy-parser-dev $(SECRETS_FILE)
	$(call db_init_f,development)
	touch $@

.init-prod: .deploy-static-prod .deploy-spider-prod .deploy-scraper-prod .deploy-parser-prod $(SECRETS_FILE)
	$(call db_init_f,production)
	touch $@

parser_notification:
	$(call add_parser_notification_f,dev)

parser_notification_production:
	$(call add_parser_notification_f,prod)

docker_image:
	$(call push_docker_image_f,dev)

docker_image_production:
	$(call push_docker_image_f,prod)

package_parser: .package-parser

package: package_parser

deploy_static: .deploy-static-dev

deploy_docker_repo: .deploy-docker-repo-dev

deploy_spider: .deploy-spider-dev

deploy_scraper: .deploy-scraper-dev

deploy_parser: .deploy-parser-dev

deploy: deploy_static deploy_docker_repo deploy_scraper deploy_parser deploy_spider .push-docker-image-dev

deploy_static_production: .deploy-static-prod

deploy_docker_repo_production: .deploy-docker-repo-prod

deploy_spider_production: .deploy-spider-prod

deploy_scraper_production: .deploy-scraper-prod

deploy_parser_production: .deploy-parser-prod

deploy_production: deploy_static_production deploy_docker_repo_production \
		deploy_scraper_production deploy_parser_production deploy_spider_production .push-docker-image-prod

init: .init-dev

init_production: .init-prod

list_exports:
	aws cloudformation list-exports

pause_scraper_service:
	$(call pause_scraper_service_f,prod)

resume_scraper_service:
	$(call resume_scraper_service_f,prod)

test:
	pytest

sync:
	rsync -av . earthseed.acab.enterprises:CaseHarvester

docs:
	rm -rf $(DOCS_DIR)
	mkdir -p $(DOCS_DIR)
	$(call create_docs_f,dev)

clean:
	rm -rf $(PACKAGE_DIR)
	rm -f .package-*
	rm -f $(foreach component,static docker-repo spider scraper parser,cloudformation/stack-$(component)-output.yaml)
	rm -rf $(DOCS_DIR)

clean_all: clean
	rm -f .deploy-*
	rm -f .create-stack-buckets
	rm -f .init-*
