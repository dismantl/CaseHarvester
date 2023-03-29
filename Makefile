PACKAGE_DIR=pkg
LIB_DIR=lib
DOCS_DIR=docs
ENV_DIR=env
SPIDER_DEPS=harvester.py \
	$(addprefix mjcs/,__init__.py spider.py config.py util.py session.py models/case.py)
SCRAPER_DEPS=harvester.py \
	$(addprefix mjcs/,__init__.py scraper.py config.py util.py session.py \
	$(addprefix models/,case.py scraper.py))
NOTIFIER_LAMBDA_DEPS=$(addprefix lambda/notifier/,notifier_lambda.py requirements.txt)
PARSER_DEPS=$(addprefix lambda/parser/,parser_lambda.py requirements.txt) \
	$(addprefix mjcs/,__init__.py config.py util.py parser/*.py models/*.py)
SECRETS_FILE=secrets.json
STACK_PREFIX=caseharvester-stack
DEFAULT_AWS_REGION=us-east-1
DB_NAME=mjcs
AWS_PROFILE=default
DOCKER_REPO_NAME=caseharvester
STACKS=static docker-repo spider scraper parser orchestrator

.PHONY: package package_parser deploy deploy_production \
	$(addprefix deploy_,$(STACKS)) \
	$(addsuffix _production,$(addprefix deploy_,$(STACKS))) \
	clean clean_all list_exports init init_production parser_notification \
	parser_notification_production docker_image docker_image_production sync docs \
	package_parser package_notifier

define deploy_stack_f
$(eval component = $(1))
$(eval environment = $(2))
$(eval env_long = $(subst prod,production,$(subst dev,development,$(environment))))
$(eval include $(ENV_DIR)/base.env)
$(eval include $(ENV_DIR)/$(env_long).env)
mkdir -p cloudformation/output
aws cloudformation package --template-file cloudformation/stack-$(component).yaml \
	--output-template-file cloudformation/output/stack-$(component)-output.yaml \
	--s3-bucket $(STACK_PREFIX)-$(component)-$(environment)-cf
aws cloudformation deploy --template-file cloudformation/output/stack-$(component)-output.yaml \
	--stack-name $(STACK_PREFIX)-$(component)-$(environment) \
	--capabilities CAPABILITY_IAM \
	--capabilities CAPABILITY_NAMED_IAM \
	--region $(DEFAULT_AWS_REGION) \
	--parameter-overrides \
		EnvironmentType=$(environment) DatabaseName=$(DB_NAME) \
		StaticStackName=$(STACK_PREFIX)-static-$(environment) \
		DockerRepoStackName=$(STACK_PREFIX)-docker-repo-$(environment) \
		SpiderStackName=$(STACK_PREFIX)-spider-$(environment) \
		ScraperStackName=$(STACK_PREFIX)-scraper-$(environment) \
		DockerRepoName=$(environment)_$(DOCKER_REPO_NAME) \
		$(shell jq -r '.$(env_long) as $$x|$$x|keys[]|. + "=" + $$x[.]' $(SECRETS_FILE))
endef

define create_stack_bucket_f
$(eval component = $(1))
$(eval environment = $(2))
aws s3api create-bucket --bucket $(STACK_PREFIX)-$(component)-$(environment)-cf --region $(DEFAULT_AWS_REGION)
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
DEV_MODE=1 python3 harvester.py --environment $(environment) \
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
$(eval AWS_ACCOUNT_ID = $(shell aws sts get-caller-identity | grep Account | cut -d'"' -f4))
$(eval SUCCESS = $(shell aws ecr get-login-password --region $(DEFAULT_AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(DEFAULT_AWS_REGION).amazonaws.com))
echo $(SUCCESS)
$(eval REPO_NAME = $(environment)_$(DOCKER_REPO_NAME))
find . -name *.pyc -delete
find . -name __pycache__ -delete
docker build --platform=linux/amd64 -t $(REPO_NAME) .
$(eval REPO_URL = $(AWS_ACCOUNT_ID).dkr.ecr.$(DEFAULT_AWS_REGION).amazonaws.com/$(REPO_NAME))
docker tag $(REPO_NAME):latest $(REPO_URL):latest
docker push $(REPO_URL)
endef

.package-parser: $(PARSER_DEPS)
	mkdir -p $(PACKAGE_DIR)/parser
	pip3 install -r lambda/parser/requirements.txt -t $(PACKAGE_DIR)/parser/
	cp lambda/parser/parser_lambda.py $(PACKAGE_DIR)/parser/
	cp -r mjcs $(PACKAGE_DIR)/parser/
	find $(PACKAGE_DIR) -name *.pyc -delete
	find $(PACKAGE_DIR) -name __pycache__ -delete
	rm -rf include
	cp -r $(LIB_DIR)/psycopg2 $(PACKAGE_DIR)/parser/
	touch $@

.package-notifier: $(NOTIFIER_LAMBDA_DEPS)
	mkdir -p $(PACKAGE_DIR)/notifier
	pip3 install -r lambda/notifier/requirements.txt -t $(PACKAGE_DIR)/notifier/
	cp lambda/notifier/notifier_lambda.py $(PACKAGE_DIR)/notifier/
	find $(PACKAGE_DIR) -name *.pyc -delete
	find $(PACKAGE_DIR) -name __pycache__ -delete
	touch $@

.create-stack-buckets:
	$(foreach env,dev prod,\
		$(foreach component,$(STACKS),\
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

.deploy-orchestrator-dev: .deploy-spider-dev .deploy-scraper-dev .package-notifier cloudformation/stack-orchestrator.yaml
	$(call deploy_stack_f,orchestrator,dev)
	touch $@

.deploy-orchestrator-prod: .deploy-spider-prod .deploy-scraper-prod .package-notifier cloudformation/stack-orchestrator.yaml
	$(call deploy_stack_f,orchestrator,prod)
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

package_notifier: .package-notifier

package: package_parser package_notifier

deploy_static: .deploy-static-dev

deploy_docker_repo: .deploy-docker-repo-dev

deploy_spider: .deploy-spider-dev

deploy_scraper: .deploy-scraper-dev

deploy_parser: .deploy-parser-dev

deploy_orchestrator: .deploy-orchestrator-dev

deploy: deploy_static deploy_docker_repo deploy_scraper deploy_parser deploy_spider deploy_orchestrator .push-docker-image-dev

deploy_static_production: .deploy-static-prod

deploy_docker_repo_production: .deploy-docker-repo-prod

deploy_spider_production: .deploy-spider-prod

deploy_scraper_production: .deploy-scraper-prod

deploy_parser_production: .deploy-parser-prod

deploy_orchestrator_production: .deploy-orchestrator-prod

deploy_production: deploy_static_production deploy_docker_repo_production \
		deploy_scraper_production deploy_parser_production deploy_spider_production \
		deploy_orchestrator_production .push-docker-image-prod

init: .init-dev

init_production: .init-prod

list_exports:
	aws cloudformation list-exports

sync:
	rsync -av . earthseed.acab.enterprises:CaseHarvester

docs:
	rm -rf $(DOCS_DIR)
	mkdir -p $(DOCS_DIR)
	$(call create_docs_f,dev)

clean:
	rm -rf $(PACKAGE_DIR)
	rm -f .package-*
	rm -rf cloudformation/output/*
	rm -rf $(DOCS_DIR)

clean_all: clean
	rm -f .deploy-*
	rm -f .create-stack-buckets
	rm -f .init-*
