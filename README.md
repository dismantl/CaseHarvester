<img src="https://openjusticebaltimore.org/images/caseharvester200h.png" alt="Case Harvester" />
<img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.mdcaseexplorer.com%2Fapi%2Fv1%2Fcases%2Fcount&label=Total%20cases&query=$.count&color=blue" alt"Total cases" />

# Case Harvester
Case Harvester is a project designed to scrape the [Maryland Judiciary Case Search](https://casesearch.courts.state.md.us/casesearch/inquiry-index.jsp) (MJCS) and build a near-complete database of Maryland court cases that can be queried and analyzed without the limitations of the MJCS interface. It is designed to leverage [Amazon Web Services (AWS)](https://aws.amazon.com/) for scalability and performance.

Our database of cases (with criminal defendant names redacted) is available to the public and can be found at [mdcaseexplorer.com](https://mdcaseexplorer.com), which is built using our [Case Explorer](https://github.com/dismantl/CaseExplorer) software. REST and GraphQL APIs are also available. If you would like to download tables from our database exported monthly, you can find that at [exports.caseharvester.com](https://exports.caseharvester.com/).

> **NOTE: Unless you are modifying Case Harvester for specific purposes, please do not run your own instance so that MJCS is spared unneccesary load. Instead, use the options described above for viewing the data, or if you have an AWS account you are also welcome to clone our database directly.**

# Architecture
> **NOTE: The diagrams below represent the architecture of Case Harvester version 1. Version 2 uses a new architecture for the spider and scraper components, which are controlled by an orchestrator written in Go. The design and usage of these components are intentionally not documented.**

Case Harvester is split into three main components: spider, scraper, and parser. Each component is a part of a pipeline that finds, downloads, and parses case data from the MJCS. The following diagram shows at a high level how each of these components interact:

![High level diagram](./img/main.svg)

### Spider
The spider component is responsible for discovering new case numbers. It does this by submitting search queries to the MJCS and iterating through the results. Because the MJCS only returns a maximum of 500 results, the search algorithm splits queries that return 500 results into a set of more narrowed queries which are then submitted. Each of these queries is then split again if more than 500 results are returned, and so forth, until the MJCS is exhaustively searched for case numbers. Each discovered case number is submitted to a PostgreSQL database, and then added to a queue for scraping:

![Spider diagram](./img/spider.svg)

### Scraper
The scraper component downloads and stores the case details for every case number discovered by the spider. The full HTML for each case ([example](https://casesearch.courts.state.md.us/casesearch/inquiryDetail.jis?caseId=116090001&loc=69&detailLoc=DSK8)) is added to an S3 bucket. Version information is kept for each case, including a timestamp of when each version was downloaded, so changes to a case can be recorded and referenced.

![Scraper diagram](./img/scraper.svg)

The scraper is a continuously running ECS service that processes case numbers from the SQS scraper queue.

### Parser
The parser component is a Lambda function that parses the fields of information in the HTML case details for each case, and stores that data in the PostgreSQL database. Each new item added to the scraper S3 bucket triggers a new parser Lambda invocation, which allows for significant scaling.

![Parser diagram](./img/parser.svg)

Case details in the MJCS are formatted differently depending on the county and type of case (e.g. district vs circuit court, criminal vs civil, etc.), and whether it is in one of the new [MDEC](https://mdcourts.gov/mdec/about)-compatible formats. MJCS [assigns a code to each of these different case types](https://www.muckrock.com/foi/maryland-154/case-search-court-classifications-56516/#comm-564971). The case details for all discovered cases are stored in S3, which are then parsed as one of the following types of cases:
* ODYCRIM: MDEC Criminal Cases
* ODYTRAF: MDEC Traffic Cases
* ODYCIVIL: MDEC Civil Cases
* ODYCVCIT: MDEC Civil Citations
* ODYCOSA: MDEC Appellate Court of Maryland (formerly Court of Special Appeals)
* ODYCOA: MDEC Supreme Court of Maryland (formerly Court of Appeals)
* DSCR: District Court Criminal Cases
* DSCIVIL: District Court Civil Cases
* DSCP: District Court Civil Citations
* DSTRAF: District Court Traffic Cases
* K: Circuit Court Criminal Cases
* CC: Circuit Court Civil Cases
* DV: Domestic Violence Cases
* DSK8: Baltimore City Criminal Cases
* PG: Prince George's County Circuit Court Criminal Cases
* PGV: Prince George's County Circuit Court Civil Cases
* MCCI: Montgomery County Civil Cases
* MCCR: Montgomery County Criminal Cases

Each different parser breaks down the case details to a granular level and stores the data in a number of database tables. This [schematic diagram](https://disman.tl/caseharvester/relationships.html) illustrates how this data is represented in the database.

# Installation
Case Harvester can be run or deployed from any workstation running Python 3.9, [GNU Make](https://www.gnu.org/software/make/), and [jq](https://stedolan.github.io/jq/). The required Python modules are in `requirements.txt` and can be installed with `pip3 install -r requirements.txt`. Creating a Python virtual environment is recommended.

Next, configure AWS CLI with `aws configure` so that it can deploy Case Harvester using your account. Here you'll use an Access Key ID and Secret Access Key either for your root AWS account, or an IAM user or role that has sufficient permissions.

## Deploy to AWS
Case Harvester uses [Cloudformation](https://aws.amazon.com/cloudformation/) stacks to deploy, configure, and connect all of the needed AWS resources. There are separate stacks for static resources (VPC, S3 bucket, RDS instance), spider, scraper, and parser. The first step is to set strong, unique passwords for the database users in `secrets.json`:

```
{
  "development":{
    "DatabaseMasterUsername":"root",
    "DatabaseMasterPassword":"badpassword",
    "DatabaseUsername":"db_user",
    "DatabasePassword":"badpassword",
    "DatabaseReadOnlyUsername":"ro_user",
    "DatabaseReadOnlyPassword":"badpassword"
  },
  "production":{
    "DatabaseMasterUsername":"root",
    "DatabaseMasterPassword":"badpassword",
    "DatabaseUsername":"db_user",
    "DatabasePassword":"badpassword",
    "DatabaseReadOnlyUsername":"ro_user",
    "DatabaseReadOnlyPassword":"badpassword"
  }
}
```

You can then deploy the cloudformation stacks to AWS by running:

```
make deploy
```

Once this is finished, you can intialize the database and configure Case Harvester to use the newly deployed resources by running:

```
make init
```

Note that the above commands deploy and initialize a development environment. To deploy to a production environment:

```
make deploy_production
make init_production
```

More make targets (such as deploying a specific stack or generating documentation) can be found by looking in the [`Makefile`](Makefile).

# Usage
You can manually run the spider (or other components) on the command line by specifying a search time range and county:
```
./src/case_harvester.py spider --start-date 1/1/2000 --end-date 12/31/2000 --county 'BALTIMORE CITY'
```

By default, `case_harvester.py` runs in your development AWS environment (see [Deploy to AWS](#deploy-to-aws)). To run in your production environment, add the `--environment production` CLI flag:

```
./src/case_harvester.py spider --environment production -s 1/1/2000 -e 12/31/2000 --county 'BALTIMORE CITY'
```

# Questions
For questions or more information, email [dan@acab.enterprises](mailto:dan@acab.enterprises).
