CODE_SRC=src
PACKAGE_DIR=pkg
LIB_DIR=lib
DOCS_DIR=docs
SPIDER_DEPS=
SCRAPER_DEPS=$(addprefix $(CODE_SRC)/,scraper/scraper_lambda.py \
	$(addprefix mjcs/,__init__.py scraper.py config.py db.py case.py session.py))
PARSER_DEPS=$(addprefix $(CODE_SRC)/,parser/parser_lambda.py \
	$(addprefix mjcs/,__init__.py config.py db.py case.py parser/*.py))
SECRETS_FILE=secrets.json
STACK_PREFIX=mjcs-stack
AWS_REGION=us-east-1
DB_NAME=mjcs

.PHONY: package $(addprefix package_,spider scraper parser) deploy \
	deploy_production $(addprefix deploy_,static spider scraper parser) \
	$(addsuffix _production,$(addprefix deploy_,static spider scraper parser)) \
	test clean clean_all list_exports init init_production parser_notification \
	sync docs

define package_f
$(eval component = $(1))
mkdir -p $(PACKAGE_DIR)/$(component)
pip3 install -r $(CODE_SRC)/$(component)/requirements.txt -t $(PACKAGE_DIR)/$(component)/
cp $(CODE_SRC)/$(component)/$(component)_lambda.py $(PACKAGE_DIR)/$(component)/
cp -r $(CODE_SRC)/mjcs $(PACKAGE_DIR)/$(component)/
rm -rf $(PACKAGE_DIR)/mjcs/_pycache_
rm -rf $(PACKAGE_DIR)/mjcs/parsers/_pycache_
endef

define deploy_stack_f
$(eval component = $(1))
$(eval environment = $(2))
aws cloudformation package --template-file cloudformation/stack-$(component).yaml \
	--output-template-file cloudformation/stack-$(component)-output.yaml \
	--s3-bucket $(STACK_PREFIX)-$(component)-$(environment)
aws cloudformation deploy --template-file cloudformation/stack-$(component)-output.yaml \
	--stack-name $(STACK_PREFIX)-$(component)-$(environment) \
	--capabilities CAPABILITY_IAM \
	--parameter-overrides \
		EnvironmentType=$(environment) DatabaseName=$(DB_NAME) \
		StaticStackName=$(STACK_PREFIX)-static-$(environment) \
		$(shell jq -r '. as $$x|keys[]|. + "=" + $$x[.]' $(SECRETS_FILE))
endef

define create_stack_bucket_f
$(eval component = $(1))
$(eval environment = $(2))
aws s3api create-bucket --bucket $(STACK_PREFIX)-$(component)-$(environment) --region $(AWS_REGION)
endef

define add_parser_notification_f
sleep 5 # so exports can propagate
$(eval environment = $(1))
$(eval bucket=$(shell aws cloudformation list-exports|grep \
	$(STACK_PREFIX)-static-$(environment)-CaseDetailsBucketName -A1|grep Value|awk '{print $$2}'))
$(eval parser_arn=$(shell aws cloudformation list-exports|grep \
	$(STACK_PREFIX)-parser-$(environment)-ParserArn -A1|grep Value|awk '{print $$2}'))
aws s3api put-bucket-notification-configuration --bucket $(bucket) \
	--notification-configuration '{"LambdaFunctionConfigurations":\
	[{"LambdaFunctionArn":$(parser_arn),"Events":["s3:ObjectCreated:*"]}]}'
endef

define db_init_f
$(eval environment = $(1))
DEV_MODE=1 python3 $(CODE_SRC)/case_harvester.py --environment $(environment) db_init \
	--db-name $(DB_NAME) --secrets-file $(SECRETS_FILE)
endef

define create_docs_f
$(eval environment = $(1))
$(eval hostname=$(shell aws cloudformation list-exports|grep \
	$(STACK_PREFIX)-static-$(environment)-DatabaseHostname -A1|grep Value|awk '{print $$2}'))
docker run -v "$(abspath $(DOCS_DIR)):/output" schemaspy/schemaspy:snapshot \
	-t pgsql \
	-db $(DB_NAME) \
	-s public \
	-u $(shell jq '.DatabaseUsername' $(SECRETS_FILE)) \
	-p $(shell jq '.DatabasePassword' $(SECRETS_FILE)) \
	-host $(hostname)
endef

.package-spider: $(SPIDER_DEPS) $(CODE_SRC)/spider/requirements.txt
	touch $@

.package-scraper: $(SCRAPER_DEPS) $(CODE_SRC)/scraper/requirements.txt
	$(call package_f,scraper)
	cp -r $(LIB_DIR)/psycopg2 $(PACKAGE_DIR)/scraper/
	touch $@

.package-parser: $(PARSER_DEPS) $(CODE_SRC)/parser/requirements.txt
	$(call package_f,parser)
	cp -r $(LIB_DIR)/psycopg2 $(PACKAGE_DIR)/parser/
	touch $@

.create-stack-buckets:
	$(foreach env,dev prod,\
		$(foreach component,static spider scraper parser,\
			$(call create_stack_bucket_f,$(component),$(env))\
		)\
	)
	touch $@

.deploy-static-dev: .create-stack-buckets cloudformation/stack-static.yaml
	$(call deploy_stack_f,static,dev)
	touch $@

.deploy-static-prod: .create-stack-buckets cloudformation/stack-static.yaml
	$(call deploy_stack_f,static,prod)
	touch $@

.deploy-spider-dev: .deploy-static-dev .package-spider cloudformation/stack-spider.yaml
	touch $@

.deploy-spider-prod: .deploy-static-prod .package-spider cloudformation/stack-spider.yaml
	touch $@

.deploy-scraper-dev: .deploy-static-dev .package-scraper cloudformation/stack-scraper.yaml
	$(call deploy_stack_f,scraper,dev)
	touch $@

.deploy-scraper-prod: .deploy-static-prod .package-scraper cloudformation/stack-scraper.yaml
	$(call deploy_stack_f,scraper,prod)
	touch $@

.deploy-parser-dev: .deploy-static-dev .package-parser cloudformation/stack-parser.yaml
	$(call deploy_stack_f,parser,dev)
	$(call add_parser_notification_f,dev)
	touch $@

.deploy-parser-prod: .deploy-static-prod .package-parser cloudformation/stack-parser.yaml
	$(call deploy_stack_f,parser,prod)
	$(call add_parser_notification_f,prod)
	touch $@

.init-dev: .deploy-static-dev .deploy-spider-dev .deploy-scraper-dev .deploy-parser-dev
	$(call db_init_f,development)
	touch $@

.init-prod: .deploy-static-prod .deploy-spider-prod .deploy-scraper-prod .deploy-parser-prod
	$(call db_init_f,production)
	touch $@

parser_notification:
	$(call add_parser_notification_f,dev)

parser_notification_production:
	$(call add_parser_notification_f,prod)

package_spider: .package-spider

package_scraper: .package-scraper

package_parser: .package-parser

package: package_spider package_scraper package_parser

deploy_static: .deploy-static-dev

deploy_spider: .deploy-spider-dev

deploy_scraper: .deploy-scraper-dev

deploy_parser: .deploy-parser-dev

deploy: deploy_static deploy_spider deploy_scraper deploy_parser

deploy_static_production: .deploy-static-prod

deploy_spider_production: .deploy-spider-prod

deploy_scraper_production: .deploy-scraper-prod

deploy_parser_production: .deploy-parser-prod

deploy_production: deploy_static_production deploy_spider_production \
		deploy_scraper_production deploy_parser_production

init: .init-dev

init_production: .init-prod

list_exports:
	aws cloudformation list-exports

test:
	pytest

sync:
	rsync -av . mjcs:mjcs

docs:
	rm -rf $(DOCS_DIR)
	mkdir -p $(DOCS_DIR)
	$(call create_docs_f,dev)

clean:
	rm -rf $(PACKAGE_DIR)
	rm -f .package-*
	rm -f $(foreach component,static spider scraper parser,cloudformation/stack-$(component)-output.yaml)
	rm -rf $(DOCS_DIR)

clean_all: clean
	rm -f .deploy-*
	rm -f .create-stack-buckets
	rm -f .init-*
