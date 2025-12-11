### Ruby Client Library Setup

Source: https://developers.google.com/google-ads/api/docs/first-call/get-campaigns

Instructions for installing and configuring the Ruby client library, including Gemfile setup and client instantiation.

```APIDOC
## Ruby Client Library Setup

### Description
This section covers the installation and setup of the Google Ads API client library for Ruby, including dependency management and client initialization.

### Installation
Add the `google-ads-googleads` gem to your Gemfile and install using bundler.

```ruby
gem 'google-ads-googleads', '~> 35.2.0'
```

Then run:

```bash
bundle install
```

### Configuration
1. **Copy and Modify `google_ads_config.rb`**: 
   Copy the `google_ads_config.rb` file from the GitHub repository and update it with your credentials.
   ```ruby
   Google::Ads::GoogleAds::Config.new do |c|
     c.developer_token = 'INSERT_DEVELOPER_TOKEN_HERE'
     c.login_customer_id = 'INSERT_LOGIN_CUSTOMER_ID_HERE'
     c.keyfile = 'JSON_KEY_FILE_PATH'
   end
   ```

### Client Instantiation
Create a `GoogleAdsClient` instance by providing the path to your configuration file.

```ruby
require 'google/ads/googleads'

# Creates a client by passing the path to the config file.
client = Google::Ads::GoogleAds::GoogleAdsClient.new('path/to/google_ads_config.rb')
```

### Example Usage (Run Campaign Report)
This example demonstrates fetching campaign data using the `GoogleAdsService.SearchStream` method.

```ruby
require 'google/ads/googleads'

def get_campaigns(customer_id)
  # GoogleAdsClient will read a config file from
  # ENV['HOME']/google_ads_config.rb when called without parameters
  client = Google::Ads::GoogleAds::GoogleAdsClient.new

  responses = client.service.google_ads.search_stream(
    customer_id: customer_id,
    query: "SELECT campaign.id, campaign.name FROM campaign ORDER BY campaign.id"
  )

  responses.each do |response|
    response.results.each do |row|
      puts "Campaign with ID #{row.campaign.id} and name '#{row.campaign.name}' was found."
    end
  end
end
```
```

--------------------------------

### Ruby Client Library Setup and Usage

Source: https://developers.google.com/google-ads/api/docs/first-call/refresh-token

Instructions for installing and configuring the Ruby client library, including credential management and a campaign retrieval example.

```APIDOC
## Ruby Client Library Setup and Usage

### Description
This section provides guidance on setting up the Google Ads Ruby client library, covering installation, credential configuration, and an example for retrieving campaigns.

### 1. Install the Gem

Add the gem to your `Gemfile` and run `bundle install`:

```ruby
gem 'google-ads-googleads', '~> 35.2.0'
```

Then run:

```bash
bundle install
```

### 2. Configure Credentials

Copy the `google_ads_config.rb` file and update it with your credentials:

```ruby
Google::Ads::GoogleAds::Config.new do |c|
  c.developer_token = 'INSERT_DEVELOPER_TOKEN_HERE'
  c.login_customer_id = 'INSERT_LOGIN_CUSTOMER_ID_HERE'
  c.keyfile = 'JSON_KEY_FILE_PATH'
end
```

### 3. Create GoogleAdsClient Instance

Instantiate the `GoogleAdsClient` by passing the path to your configuration file:

```ruby
client = Google::Ads::GoogleAds::GoogleAdsClient.new('path/to/google_ads_config.rb')
```

### 4. Retrieve Campaigns

Use the `GoogleAdsService.SearchStream` method to fetch campaign data:

```ruby
def get_campaigns(customer_id)
  # GoogleAdsClient will read a config file from
  # ENV['HOME']/google_ads_config.rb when called without parameters
  client = Google::Ads::GoogleAds::GoogleAdsClient.new

  responses = client.service.google_ads.search_stream(
    customer_id: customer_id,
    query: "SELECT campaign.id, campaign.name FROM campaign ORDER BY campaign.id"
  )

  responses.each do |response|
    response.results.each do |row|
      puts "Campaign with ID #{row.campaign.id} and name '#{row.campaign.name}' was found."
    end
  end
end
```

```

--------------------------------

### Ruby Client Library Setup and Campaign Retrieval

Source: https://developers.google.com/google-ads/api/docs/get-started/make-first-call

Instructions for installing the Ruby client library, configuring credentials, and retrieving campaigns using the GoogleAdsService.SearchStream method.

```APIDOC
## Ruby Client Library

### Description
This section outlines the process of installing the Google Ads API client library for Ruby using Bundler, configuring credentials, and an example of how to retrieve campaign data.

### Installation

Add the gem to your Gemfile and run bundle install.

```ruby
gem 'google-ads-googleads', '~> 35.2.0'
```

Then run:

```bash
bundle install
```

### Configuration

1.  **Copy Configuration File**: Make a copy of the `google_ads_config.rb` file from the GitHub repository.
2.  **Modify Credentials**: Update the file with your credentials.

```ruby
Google::Ads::GoogleAds::Config.new do |c|
  c.developer_token = 'INSERT_DEVELOPER_TOKEN_HERE'
  c.login_customer_id = 'INSERT_LOGIN_CUSTOMER_ID_HERE'
  c.keyfile = 'JSON_KEY_FILE_PATH'
end
```

### Client Instantiation

Create a `GoogleAdsClient` instance by passing the path to your configuration file.

```ruby
client = Google::Ads::GoogleAds::GoogleAdsClient.new('path/to/google_ads_config.rb')
```

### Retrieving Campaigns

Use the `GoogleAdsService.SearchStream` method to retrieve campaign data. The client can also read configuration from `ENV['HOME']/google_ads_config.rb` if no path is provided.

```ruby
def get_campaigns(customer_id)
  # GoogleAdsClient will read a config file from
  # ENV['HOME']/google_ads_config.rb when called without parameters
  client = Google::Ads::GoogleAds::GoogleAdsClient.new

  responses = client.service.google_ads.search_stream(
    customer_id: customer_id,
  )
end
```
```

--------------------------------

### Python Client Library Setup and Usage

Source: https://developers.google.com/google-ads/api/docs/first-call/refresh-token

Instructions for installing and configuring the Python client library, including credential management and a campaign retrieval example.

```APIDOC
## Python Client Library Setup and Usage

### Description
This section covers the installation, credential setup, and usage of the Google Ads Python client library, including an example for retrieving campaigns.

### 1. Install the Client Library

Install the library using pip:

```bash
python -m pip install google-ads==21.3.0
```

### 2. Configure Credentials

Copy the `google-ads.yaml` file and update it with your credentials:

```yaml
developer_token: INSERT_DEVELOPER_TOKEN_HERE
login_customer_id: INSERT_LOGIN_CUSTOMER_ID_HERE
json_key_file_path: JSON_KEY_FILE_PATH_HERE
```

### 3. Create GoogleAdsClient Instance

Instantiate the `GoogleAdsClient` by loading from your configuration file:

```python
from google.ads.googleads.client import GoogleAdsClient

client = GoogleAdsClient.load_from_storage("path/to/google-ads.yaml")
```

### 4. Configure Logging (Optional)

Add a handler to the library's logger to direct logs to stdout:

```python
import logging
import sys

logger = logging.getLogger('google.ads.googleads.client')
logger.addHandler(logging.StreamHandler(sys.stdout))
```

### 5. Retrieve Campaigns

Use the `GoogleAdsService.SearchStream` method to fetch campaign data:

```python
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from typing import Iterator, List
from google.ads.googleads.services import GoogleAdsServiceClient
from google.ads.googleads.batch_job_service import BatchJobService
from google.ads.googleads.proto.resources.types import GoogleAdsRow
from google.ads.googleads.proto.services.types import SearchGoogleAdsStreamResponse

def main(client: GoogleAdsClient, customer_id: str) -> None:
    ga_service: GoogleAdsServiceClient = client.get_service("GoogleAdsService")

    query: str = """
        SELECT
          campaign.id,
          campaign.name
        FROM campaign
        ORDER BY campaign.name    """

    # Issues a search request using streaming.
    stream: Iterator[SearchGoogleAdsStreamResponse] = ga_service.search_stream(
        customer_id=customer_id, query=query
    )

    for batch in stream:
        rows: List[GoogleAdsRow] = batch.results
        for row in rows:
            print(
                f"Campaign with ID {row.campaign.id} and name "
                f'"{row.campaign.name}" was found.'
            )
# get_campaigns.py
```

```

--------------------------------

### Python Client Library Setup

Source: https://developers.google.com/google-ads/api/docs/first-call/get-campaigns

Instructions for installing and configuring the Python client library, including credential management and client instantiation.

```APIDOC
## Python Client Library Setup

### Description
This section guides you through installing and setting up the Google Ads API client library for Python, including credential management and client initialization.

### Installation
Install the client library using pip:

```bash
python -m pip install google-ads==21.3.0
```

### Configuration
1. **Copy and Modify `google-ads.yaml`**: 
   Copy the `google-ads.yaml` file from the GitHub repository and update it with your credentials.
   ```yaml
   developer_token: INSERT_DEVELOPER_TOKEN_HERE
   login_customer_id: INSERT_LOGIN_CUSTOMER_ID_HERE
   json_key_file_path: JSON_KEY_FILE_PATH_HERE
   ```

### Client Instantiation
Create a `GoogleAdsClient` instance by loading from your storage configuration.

```python
from google.ads.googleads.client import GoogleAdsClient

# Constructs the GoogleAdsClient object.
client = GoogleAdsClient.load_from_storage("path/to/google-ads.yaml")
```

### Logging Setup
Add a handler to the library's logger to direct output to the console.

```python
import logging
import sys

logger = logging.getLogger('google.ads.googleads.client')
logger.addHandler(logging.StreamHandler(sys.stdout))
```

### Example Usage (Run Campaign Report)
This example shows how to fetch campaign data using the `GoogleAdsService.SearchStream` method.

```python
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.services import GoogleAdsServiceClient
from google.ads.googleads.types import SearchGoogleAdsStreamResponse, GoogleAdsRow
from typing import Iterator, List

def main(client: GoogleAdsClient, customer_id: str) -> None:
    ga_service: GoogleAdsServiceClient = client.get_service("GoogleAdsService")

    query: str = """
        SELECT
          campaign.id,
          campaign.name
        FROM campaign
        ORDER BY campaign.id"""

    # Issues a search request using streaming.
    stream: Iterator[SearchGoogleAdsStreamResponse] = ga_service.search_stream(
        customer_id=customer_id, query=query
    )

    for batch in stream:
        rows: List[GoogleAdsRow] = batch.results
        for row in rows:
            print(
                f"Campaign with ID {row.campaign.id} and name "
                f'"{row.campaign.name}" was found.'
            )
# get_campaigns.py
```
```

--------------------------------

### Python Client Library Setup and Campaign Retrieval

Source: https://developers.google.com/google-ads/api/docs/get-started/make-first-call

Instructions for installing the Python client library, configuring credentials, and retrieving campaigns using the GoogleAdsService.SearchStream method.

```APIDOC
## Python Client Library

### Description
This section provides instructions for installing and configuring the Google Ads API client library for Python, along with an example for retrieving campaign data.

### Installation

Install the client library using pip.

```bash
python -m pip install google-ads==21.3.0
```

### Configuration

1.  **Copy Configuration File**: Make a copy of the `google-ads.yaml` file from the GitHub repository.
2.  **Modify Credentials**: Update the copied file with your credentials.

```yaml
developer_token: INSERT_DEVELOPER_TOKEN_HERE
login_customer_id: INSERT_LOGIN_CUSTOMER_ID_HERE
json_key_file_path: JSON_KEY_FILE_PATH_HERE
```

### Client Instantiation

Create a `GoogleAdsClient` instance by loading from your storage configuration.

```python
from google.ads.googleads.client import GoogleAdsClient

client = GoogleAdsClient.load_from_storage("path/to/google-ads.yaml")
```

### Logging

Add a handler to the library's logger to direct output to the console.

```python
import logging
import sys

logger = logging.getLogger('google.ads.googleads.client')
logger.addHandler(logging.StreamHandler(sys.stdout))
```

### Retrieving Campaigns

Use the `GoogleAdsService.SearchStream` method to retrieve campaign data.

```python
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from typing import Iterator, List
from google.ads.googleads.v15.services.types import SearchGoogleAdsStreamResponse
from google.ads.googleads.v15.resources.types import GoogleAdsRow

def main(client: GoogleAdsClient, customer_id: str) -> None:
    ga_service: GoogleAdsServiceClient = client.get_service("GoogleAdsService")

    query: str = """
        SELECT
          campaign.id,
          campaign.name
        FROM campaign
        ORDER BY campaign.id"""

    # Issues a search request using streaming.
    stream: Iterator[SearchGoogleAdsStreamResponse] = ga_service.search_stream(
        customer_id=customer_id, query=query
    )

    for batch in stream:
        rows: List[GoogleAdsRow] = batch.results
        for row in rows:
            print(
                f"Campaign with ID {row.campaign.id} and name "
                f'"{row.campaign.name}" was found.'
            )
```

*File: get_campaigns.py*
```

--------------------------------

### Getting Started Guide

Source: https://developers.google.com/google-ads/api/docs/client-libs/java_hl=id

Provides setup instructions for using the Google Ads API Client Library for Java.

```APIDOC
## Getting Started with the Google Ads API Client Library for Java

### Description
This guide outlines the initial setup steps required to begin using the Google Ads API Client Library for Java.

### Method
Setup

### Steps
1. **Prerequisites**: Ensure you have Java 1.8 or later installed.
2. **Dependency**: Add the Google Ads API client library for Java to your project's dependencies (e.g., via Maven or Gradle).
3. **Configuration**: Configure your API access credentials (e.g., OAuth2 client ID and secret).
4. **Client Instantiation**: Create an instance of the Google Ads API client service.

### Further Reading
- [Authorization Guide](#authorization)
- [Build from source](#build-from-source)
```

--------------------------------

### Getting Started with Google Ads API .NET Client Library

Source: https://developers.google.com/google-ads/api/docs/client-libs/dotnet/getting-started_hl=fa

This section covers the initial steps to set up and use the Google Ads API .NET client library, including installation, configuration, and basic usage.

```APIDOC
## Getting Started with Google Ads API .NET Client Library

This guide provides an overview of how to get started with the Google Ads API .NET client library.

### Installation

Install the client library using NuGet:

```bash
Install-Package Google.Ads.GoogleAds
```

### Setting Up Credentials

You need to configure your authentication credentials. This typically involves obtaining a developer token, client ID, client secret, and refresh token.

**If you need to generate credentials:**

1.  Follow the [Developer token guide](https://developers.google.com/google-ads/api/docs/first-call/dev-token) to get your developer token.
2.  Follow the [OAuth desktop app flow guide](https://developers.google.com/google-ads/api/docs/authentication/oauth-desktop) to generate your client ID, client secret, and refresh token.

**If you already have credentials:**

Copy the `GoogleAdsApi` node and the `GoogleAdsApi` section under the `configSections` node from the example `App.config` file on GitHub into your `App.config` or `Web.config` file. These nodes are automatically imported if you used NuGet to install the package.

Place your developer token, client ID, client secret, and refresh token into your application's `App.config` / `Web.config` file.

The `App.config` file on GitHub is fully documented. Refer to the [configuration guide](https://github.com/googleads/googleads-dotnet-lib/blob/master/docs/configuration.md) for more information and alternative configuration methods like environment variables.

### Making an API Call

Here's how to create a `GoogleAdsClient` and make an API call:

**1. Create a `GoogleAdsClient` instance:**

The `GoogleAdsClient` class is central to the Google Ads API .NET library. It allows you to create pre-configured service classes for making API calls. The default constructor creates a user object using settings from your `App.config` / `Web.config` file.

```csharp
// Create a Google Ads client using App.config settings.
GoogleAdsClient client = new GoogleAdsClient();
```

**2. Create a Service:**

Use the `GetService` method of the `GoogleAdsClient` to create a service instance. The `Services` class provides enumerations for all supported API versions and services.

```csharp
// Create the required service (e.g., CampaignService for V21).
CampaignServiceClient campaignService = client.GetService(Services.V21.CampaignService);

// Now you can make calls to the CampaignService.
// For example:
// var response = campaignService.SearchStream(...);
```

### Thread Safety

It is not safe to share a `GoogleAdsClient` instance across multiple threads. Configuration changes made in one thread might affect services created in other threads. However, operations like getting new service instances from a `GoogleAdsClient` and making calls to multiple services in parallel are generally safe.

**Example of a multi-threaded application:**

```csharp
// Create separate GoogleAdsClient instances for each thread.
GoogleAdsClient client1 = new GoogleAdsClient();
GoogleAdsClient client2 = new GoogleAdsClient();

Thread userThread1 = new Thread(AddAdGroups);
Thread userThread2 = new Thread(AddAdGroups);

userThread1.Start(client1);
userThread2.Start(client2);

userThread1.Join();
userThread2.Join();

public void AddAdGroups(object data) {
    GoogleAdsClient client = (GoogleAdsClient)data;
    // Perform operations using the provided client instance.
    // ...
}
```
```

--------------------------------

### PHP Client Library Setup and Campaign Retrieval

Source: https://developers.google.com/google-ads/api/docs/get-started/make-first-call

Instructions for installing the PHP client library, configuring credentials, and retrieving campaigns using the GoogleAdsService.SearchStream method.

```APIDOC
## PHP Client Library

### Description
This section details how to set up and use the Google Ads API client library for PHP. It covers credential configuration and an example of retrieving campaign data.

### Installation

This guide doesn't cover installation details but assumes you have the library installed.

### Configuration

1.  **Copy Configuration File**: Make a copy of the `google_ads_php.ini` file from the GitHub repository.
2.  **Modify Credentials**: Update the copied file with your actual credentials.

```ini
[GOOGLE_ADS]
developerToken = "INSERT_DEVELOPER_TOKEN_HERE"
loginCustomerId = "INSERT_LOGIN_CUSTOMER_ID_HERE"

[OAUTH2]
jsonKeyFilePath = "INSERT_ABSOLUTE_PATH_TO_OAUTH2_JSON_KEY_FILE_HERE"
scopes = "https://www.googleapis.com/auth/adwords"
```

### Client Instantiation

Create an instance of the `GoogleAdsClient` object.

```php
use GoogleAdsGoogleAdsLibOAuth2TokenBuilder;
use GoogleAdsGoogleAdsLibGoogleAdsClientBuilder;

$oAuth2Credential = (new OAuth2TokenBuilder())
    ->fromFile('/path/to/google_ads_php.ini')
    ->build();

$googleAdsClient = (new GoogleAdsClientBuilder())
    ->fromFile('/path/to/google_ads_php.ini')
    ->withOAuth2Credential($oAuth2Credential)
    ->build();
```

### Retrieving Campaigns

Use the `GoogleAdsService.SearchStream` method to retrieve campaign data.

```php
use GoogleAdsGoogleAdsLibGoogleAdsClient;
use GoogleAdsGoogleAdsLibGoogleAdsServerStreamDecorator;
use GoogleAdsGoogleAdsV15ServicesSearchGoogleAdsStreamRequest;
use GoogleAdsGoogleAdsV15ResourcesGoogleAdsRow;

public static function runExample(GoogleAdsClient $googleAdsClient, int $customerId)
{
    $googleAdsServiceClient = $googleAdsClient->getGoogleAdsServiceClient();
    // Creates a query that retrieves all campaigns.
    $query = 'SELECT campaign.id, campaign.name FROM campaign ORDER BY campaign.id';
    // Issues a search stream request.
    /** @var GoogleAdsServerStreamDecorator $stream */
    $stream = $googleAdsServiceClient->searchStream(
        SearchGoogleAdsStreamRequest::build($customerId, $query)
    );

    // Iterates over all rows in all messages and prints the requested field values for
    // the campaign in each row.
    foreach ($stream->iterateAllElements() as $googleAdsRow) {
        /** @var GoogleAdsRow $googleAdsRow */
        printf(
            "Campaign with ID %d and name '%s' was found.%s",
            $googleAdsRow->getCampaign()->getId(),
            $googleAdsRow->getCampaign()->getName(),
            PHP_EOL
        );
    }
}
```

*File: GetCampaigns.php*
```

--------------------------------

### C# Client Library Setup and Campaign Retrieval

Source: https://developers.google.com/google-ads/api/docs/first-call/get-campaigns

Instructions for setting up the C# client library for Google Ads, including NuGet package installation, configuration, and an example of retrieving campaigns using `GoogleAdsService.SearchStream`.

```APIDOC
## C# Client Library

### Description
This section details how to set up and use the Google Ads API C# client library to retrieve campaign information.

### NuGet Package Installation
Run the following command:
```bash
dotnet add package Google.Ads.GoogleAds --version 18.1.0
```

### Configuration
Create a `GoogleAdsConfig` object with the relevant settings:
```csharp
GoogleAdsConfig config = new GoogleAdsConfig()
{
    DeveloperToken = "******",
    OAuth2Mode = OAuth2Flow.SERVICE_ACCOUNT,
    OAuth2SecretsJsonPath = "PATH_TO_CREDENTIALS_JSON",
    LoginCustomerId = ******
};
GoogleAdsClient client = new GoogleAdsClient(config);
```

### Retrieve Campaigns
```csharp
public void Run(GoogleAdsClient client, long customerId)
{
    // Get the GoogleAdsService.
    GoogleAdsServiceClient googleAdsService = client.GetService(
        Services.V21.GoogleAdsService);

    // Create a query that will retrieve all campaigns.
    string query = @"SELECT
                    campaign.id,
                    campaign.name,
                    campaign.network_settings.target_content_network
                FROM campaign
                ORDER BY campaign.id";

    try
    {
        // Issue a search request.
        googleAdsService.SearchStream(customerId.ToString(), query,
            delegate (SearchGoogleAdsStreamResponse resp)
            {
                foreach (GoogleAdsRow googleAdsRow in resp.Results)
                {
                    Console.WriteLine("Campaign with ID {0} and name '{1}' was found.",
                        googleAdsRow.Campaign.Id, googleAdsRow.Campaign.Name);
                }
            }
        );
    }
    catch (GoogleAdsException e)
    {
        Console.WriteLine("Failure:");
        Console.WriteLine($"Message: {e.Message}");
        Console.WriteLine($"Failure: {e.Failure}");
        Console.WriteLine($"Request ID: {e.RequestId}");
        throw;
    }
}
```
```

--------------------------------

### PHP Client Library Setup

Source: https://developers.google.com/google-ads/api/docs/first-call/refresh-token

Instructions for installing the Google Ads PHP client library using Composer.

```APIDOC
## Composer Installation
```bash
composer require googleads/google-ads-php:31.0.0
```
```

--------------------------------

### Google Ads Perl Setup and Campaign Retrieval

Source: https://developers.google.com/google-ads/api/docs/first-call/get-campaigns

Instructions for setting up the google-ads-perl library, including cloning the repository, installing dependencies, configuring credentials, and an example of retrieving campaign data using `GoogleAdsService.SearchStream`.

```APIDOC
## Google Ads Perl Setup and Campaign Retrieval

### Description
This section details how to set up and use the `google-ads-perl` library to interact with the Google Ads API. It covers cloning the repository, installing dependencies, configuring authentication, and provides a code example for fetching campaign information.

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/googleads/google-ads-perl.git
    ```
2.  **Navigate to the directory:**
    ```bash
    cd google-ads-perl
    ```
3.  **Install dependencies:**
    ```bash
    cpan install Module::Build
    perl Build.PL
    perl Build installdeps
    ```

### Authentication

1.  **Copy and modify `googleads.properties`:**
    Make a copy of the `googleads.properties` file from the repository and update it with your credentials:
    ```properties
    jsonKeyFilePath=JSON_KEY_FILE_PATH
    developerToken=INSERT_DEVELOPER_TOKEN_HERE
    loginCustomerId=INSERT_LOGIN_CUSTOMER_ID_HERE
    ```

2.  **Create a `Client` instance:**
    Pass the path to your properties file when creating the client:
    ```perl
    my $properties_file = "/path/to/googleads.properties";

    my $api_client = Google::Ads::GoogleAds::Client->new({
      properties_file => $properties_file
    });
    ```

### Campaign Retrieval Example

This Perl subroutine demonstrates how to retrieve campaigns using the `GoogleAdsService.SearchStream` method.

```perl
sub get_campaigns {
  my ($api_client, $customer_id) = @_;

  # Create a search Google Ads stream request that will retrieve all campaigns.
  my $search_stream_request =
    Google::Ads::GoogleAds::V21::Services::GoogleAdsService::SearchGoogleAdsStreamRequest
    ->new({
      customerId => $customer_id,
      query      =>
        "SELECT campaign.id, campaign.name FROM campaign ORDER BY campaign.id"
    });

  # Get the GoogleAdsService.
  my $google_ads_service = $api_client->GoogleAdsService();

  my $search_stream_handler =
    Google::Ads::GoogleAds::Utils::SearchStreamHandler->new({
      service => $google_ads_service,
      request => $search_stream_request
    });

  # Issue a search request and process the stream response to print the requested
  # field values for the campaign in each row.
  $search_stream_handler->process_contents(
    sub {
      my $google_ads_row = shift;
      printf "Campaign with ID %d and name \'%s\' was found.\n",
        $google_ads_row->{campaign}{id},
        $google_ads_row->{campaign}{name};
    });

  return 1;
}
```
```

--------------------------------

### PHP Client Library Setup

Source: https://developers.google.com/google-ads/api/docs/get-started/select-account

Instructions for installing the PHP client library using Composer.

```APIDOC
## Composer Installation

Change into the root directory of your project and run the following command to install the library and all its dependencies in the `vendor/` directory of your project's root directory.

```bash
composer require googleads/google-ads-php:31.0.0
```
```

--------------------------------

### Setting up a Maven Project

Source: https://developers.google.com/google-ads/api/docs/client-libs/java/quick-start_hl=tr

Instructions and code examples for setting up a new Maven project with the Google Ads API, including importing the Bill of Materials (BOM) for dependency management.

```APIDOC
## New Maven/Gradle Project Setup

To use the Google Ads API client library, it's recommended to use Apache Maven or Gradle. Your builds are published to the Maven central repository.

### Maven Dependency

```xml
<dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>com.google.api-ads</groupId>
      <artifactId>google-ads-bom</artifactId>
      <version>40.0.0</version>
      <type>pom</type>
      <scope>import</scope>
    </dependency>
  </dependencies>
</dependencyManagement>

<dependency>
  <groupId>com.google.api-ads</groupId>
  <artifactId>google-ads</artifactId>
</dependency>
```

### Gradle Dependency

```gradle
implementation platform('com.google.api-ads:google-ads-bom:40.0.0')
implementation 'com.google.api-ads:google-ads'
```
```

--------------------------------

### Ruby - Get Campaigns

Source: https://developers.google.com/google-ads/api/docs/get-started/make-first-call_hl=zh-cn

This Ruby example demonstrates how to install the client library, configure credentials, and fetch campaign information using the Google Ads API.

```APIDOC
## GET /googleads/v1/campaigns

### Description
Retrieves a list of campaigns from your Google Ads account.

### Method
GET

### Endpoint
/googleads/v1/campaigns

### Parameters
#### Query Parameters
- **customerId** (string) - Required - The ID of the customer account.

### Request Body
This endpoint does not have a request body.

### Request Example
```ruby
require 'google/ads/googleads'

# Initialize Google Ads client with configuration
# Assumes google_ads_config.rb is in the default location or specified by ENV['GOOGLE_ADS_CONFIG_PATH']
client = Google::Ads::GoogleAds::GoogleAdsClient.new

# Define customer ID
customer_id = "YOUR_CUSTOMER_ID"

# Perform the search stream request
responses = client.service.google_ads.search_stream(
  customer_id: customer_id,
  query: 'SELECT campaign.id, campaign.name FROM campaign ORDER BY campaign.id'
)

# Process the responses
responses.each do |response|
  response.results.each do |row|
    puts "Campaign with ID #{row.campaign.id} and name '#{row.campaign.name}' was found."
  end
end
```

### Response
#### Success Response (200)
- **campaign.id** (integer) - The ID of the campaign.
- **campaign.name** (string) - The name of the campaign.

#### Response Example
```json
[
  {
    "results": [
      {
        "campaign": {
          "id": 1234567890,
          "name": "Example Campaign"
        }
      }
    ]
  }
]
```
```

--------------------------------

### Run Google Ads API Examples with Gradle

Source: https://developers.google.com/google-ads/api/docs/client-libs/java/getting-started

This snippet shows how to execute a specific Google Ads API example using the Gradle wrapper. The `--example` parameter specifies the example to run, and `--help` can be used to display usage instructions for that example.

```bash
./gradlew -q runExample --example="basicoperations.GetCampaigns --help"
```

--------------------------------

### Ruby Client Library - Get Campaigns

Source: https://developers.google.com/google-ads/api/docs/get-started/make-first-call_hl=zh-tw

This example shows how to fetch campaigns using the Ruby Google Ads client library. It covers installation via Bundler, configuration file setup, client instantiation, and making a search stream request.

```APIDOC
## GET /campaigns

### Description
Retrieves a list of all campaigns within a Google Ads account.

### Method
GET

### Endpoint
`/campaigns`

### Parameters
#### Query Parameters
- **customerId** (string) - Required - The ID of the customer account.

### Request Example
```ruby
# Add to Gemfile
# gem 'google-ads-googleads', '~> 35.2.0'
# bundle install

# Configure credentials in google_ads_config.rb
# Google::Ads::GoogleAds::Config.new do |c|
#   c.developer_token = 'INSERT_DEVELOPER_TOKEN_HERE'
#   c.login_customer_id = 'INSERT_LOGIN_CUSTOMER_ID_HERE'
#   c.keyfile = 'JSON_KEY_FILE_PATH'
# end

require 'google/ads/google_ads'

# Initialize client
client = Google::Ads::GoogleAds::GoogleAdsClient.new('path/to/google_ads_config.rb')

def get_campaigns(client: GoogleAdsClient, customer_id: String)
  responses = client.service.google_ads.search_stream(
    customer_id: customer_id,
    query: 'SELECT campaign.id, campaign.name FROM campaign ORDER BY campaign.id',
  )

  responses.each do |response|
    response.results.each do |row|
      puts "Campaign with ID #{row.campaign.id} and name '#{row.campaign.name}' was found."
    end
  end
end

# Example usage:
# get_campaigns(client: client, customer_id: "YOUR_CUSTOMER_ID")
```

### Response
#### Success Response (200)
- **campaign.id** (integer) - The ID of the campaign.
- **campaign.name** (string) - The name of the campaign.

#### Response Example
```json
{
  "campaign": {
    "id": "1234567890",
    "name": "Example Campaign"
  }
}
```
```

--------------------------------

### PHP: Composer Installation

Source: https://developers.google.com/google-ads/api/docs/get-started/make-first-call

Instructions for installing the Google Ads PHP client library using Composer.

```APIDOC
## PHP: Composer Installation

### Description
This section provides instructions on how to install the Google Ads PHP client library using Composer, a dependency manager for PHP.

### Installation

Navigate to your project's root directory and run the following command:

```bash
composer require googleads/google-ads-php:31.0.0
```
```

--------------------------------

### Installation

Source: https://developers.google.com/google-ads/api/docs/client-libs/dotnet/getting-started_hl=es-419

Install the Google Ads API .NET client library by adding a NuGet package reference to the `Google.Ads.GoogleAds` package in your project.

```APIDOC
## Installation

The client library binaries are distributed via NuGet. Add a NuGet package reference to the `Google.Ads.GoogleAds` package to your project to use the client library.
```

--------------------------------

### PHP Client Library Setup and Usage

Source: https://developers.google.com/google-ads/api/docs/first-call/refresh-token

Instructions for configuring the PHP client library, including credentials management and a basic campaign retrieval example.

```APIDOC
## PHP Client Library Setup and Usage

### Description
This section details how to set up the Google Ads PHP client library, including credential configuration and an example of retrieving campaigns.

### 1. Configure Credentials

Copy the `google_ads_php.ini` file and update it with your credentials:

```ini
[GOOGLE_ADS]
developerToken = "INSERT_DEVELOPER_TOKEN_HERE"
loginCustomerId = "INSERT_LOGIN_CUSTOMER_ID_HERE"

[OAUTH2]
jsonKeyFilePath = "INSERT_ABSOLUTE_PATH_TO_OAUTH2_JSON_KEY_FILE_HERE"
scopes = "https://www.googleapis.com/auth/adwords"
```

### 2. Create GoogleAdsClient Instance

Instantiate the `GoogleAdsClient` using your configuration file:

```php
use GoogleAdsApiCommonOAuth2TokenBuilder;
use GoogleAdsApiGoogleAdsGoogleAdsClientBuilder;

$oAuth2Credential = (new OAuth2TokenBuilder())
    ->fromFile('/path/to/google_ads_php.ini')
    ->build();

$googleAdsClient = (new GoogleAdsClientBuilder())
    ->fromFile('/path/to/google_ads_php.ini')
    ->withOAuth2Credential($oAuth2Credential)
    ->build();
```

### 3. Retrieve Campaigns

Use the `GoogleAdsService.SearchStream` method to fetch campaign data:

```php
use GoogleAdsApiGoogleAdsGoogleAdsClient;
use GoogleAdsApiGoogleAdsServicesGoogleAdsServerStreamDecorator;
use GoogleAdsApiGoogleAdsGoogleAdsRow;
use GoogleAdsApiGoogleAdsReportingSearchGoogleAdsStreamRequest;

public static function runExample(GoogleAdsClient $googleAdsClient, int $customerId)
{
    $googleAdsServiceClient = $googleAdsClient->getGoogleAdsServiceClient();
    // Creates a query that retrieves all campaigns.
    $query = 'SELECT campaign.id, campaign.name FROM campaign ORDER BY campaign.id';
    // Issues a search stream request.
    /** @var GoogleAdsServerStreamDecorator $stream */
    $stream = $googleAdsServiceClient->searchStream(
        SearchGoogleAdsStreamRequest::build($customerId, $query)
    );

    // Iterates over all rows in all messages and prints the requested field values for
    // the campaign in each row.
    foreach ($stream->iterateAllElements() as $googleAdsRow) {
        /** @var GoogleAdsRow $googleAdsRow */
        printf(
            "Campaign with ID %d and name '%s' was found.%s",
            $googleAdsRow->getCampaign()->getId(),
            $googleAdsRow->getCampaign()->getName(),
            PHP_EOL
        );
    }
}
// GetCampaigns.php
```

```

--------------------------------

### Installation

Source: https://developers.google.com/google-ads/api/docs/client-libs/dotnet/getting-started_hl=zh-tw

The client library binaries are released through NuGet. Add a NuGet reference to the `Google.Ads.GoogleAds` package in your project to use the client library.

```APIDOC
## Installation

The client library binaries are released through NuGet. Add a NuGet reference to the `Google.Ads.GoogleAds` package in your project to use the client library.
```

--------------------------------

### Google Ads API - Getting Started Guide

Source: https://developers.google.com/google-ads/api/docs/things-to-do-ads/overview_hl=zh-tw

A step-by-step guide for using the Google Ads API to create campaigns, ad groups, and ads.

```APIDOC
## Getting Started with Google Ads API

### Description
This guide outlines the necessary steps to create campaigns, ad groups, and ads using the Google Ads API.

### Steps
1. **Create Campaign**
2. **Create Ad Group**
3. **Create Ad Group Ad**
4. **Create Merchant Group**
5. **Reporting**
```

--------------------------------

### PHP Client Library Setup

Source: https://developers.google.com/google-ads/api/docs/first-call/get-campaigns

Instructions for configuring the PHP client library, including credentials and client instantiation.

```APIDOC
## PHP Client Library Setup

### Description
This section details how to set up the Google Ads API client library for PHP, including credential configuration and client instantiation.

### Configuration
1. **Copy and Modify `google_ads_php.ini`**:
   Make a copy of the `google_ads_php.ini` file from the GitHub repository and update it with your credentials.
   ```ini
   [GOOGLE_ADS]
   developerToken = "INSERT_DEVELOPER_TOKEN_HERE"
   loginCustomerId = "INSERT_LOGIN_CUSTOMER_ID_HERE"

   [OAUTH2]
   jsonKeyFilePath = "INSERT_ABSOLUTE_PATH_TO_OAUTH2_JSON_KEY_FILE_HERE"
   scopes = "https://www.googleapis.com/auth/adwords"
   ```

### Client Instantiation
Create an instance of the `GoogleAdsClient` object using your configuration.

```php
<?php

use GoogleAdsApiCommonOAuth2TokenBuilder;
use GoogleAdsApiGoogleAdsGoogleAdsClientBuilder;

// Builds the OAuth2 credential provider.
$oAuth2Credential = (new OAuth2TokenBuilder())
    ->fromFile('/path/to/google_ads_php.ini')
    ->build();

// Constructs the Google Ads client.
$googleAdsClient = (new GoogleAdsClientBuilder())
    ->fromFile('/path/to/google_ads_php.ini')
    ->withOAuth2Credential($oAuth2Credential)
    ->build();

?>
```

### Example Usage (Run Campaign Report)
This example demonstrates how to retrieve campaigns using the `GoogleAdsService.SearchStream` method.

```php
<?php

use GoogleAdsApiGoogleAdsGoogleAdsClient;
use GoogleAdsApiGoogleAdsGoogleAdsServerStreamDecorator;
use GoogleAdsApiGoogleAdsProtoSearchGoogleAdsStreamRequest;
use GoogleAdsApiGoogleAdsProtoGoogleAdsRow;

public static function runExample(GoogleAdsClient $googleAdsClient, int $customerId)
{
    $googleAdsServiceClient = $googleAdsClient->getGoogleAdsServiceClient();
    // Creates a query that retrieves all campaigns.
    $query = 'SELECT campaign.id, campaign.name FROM campaign ORDER BY campaign.id';
    // Issues a search stream request.
    /** @var GoogleAdsServerStreamDecorator $stream */
    $stream = $googleAdsServiceClient->searchStream(
        SearchGoogleAdsStreamRequest::build($customerId, $query)
    );

    // Iterates over all rows in all messages and prints the requested field values for
    // the campaign in each row.
    foreach ($stream->iterateAllElements() as $googleAdsRow) {
        /** @var GoogleAdsRow $googleAdsRow */
        printf(
            "Campaign with ID %d and name '%s' was found.%s",
            $googleAdsRow->getCampaign()->getId(),
            $googleAdsRow->getCampaign()->getName(),
            PHP_EOL
        );
    }
}
// GetCampaigns.php

?>
```
```

--------------------------------

### PHP Client Library Installation

Source: https://developers.google.com/google-ads/api/docs/first-call/get-campaigns

Instructions for installing the PHP client library for Google Ads using Composer.

```APIDOC
## PHP Client Library

### Description
This section provides instructions for installing the Google Ads API PHP client library.

### Installation
Change into the root directory of your project and run the following command:
```bash
composer require googleads/google-ads-php:31.0.0
```
```

--------------------------------

### Python - Get Campaigns

Source: https://developers.google.com/google-ads/api/docs/get-started/make-first-call_hl=zh-cn

This Python example shows how to install the client library, configure credentials, and retrieve a list of campaigns using the Google Ads API.

```APIDOC
## GET /googleads/v1/campaigns

### Description
Retrieves a list of campaigns from your Google Ads account.

### Method
GET

### Endpoint
/googleads/v1/campaigns

### Parameters
#### Query Parameters
- **customerId** (string) - Required - The ID of the customer account.

### Request Body
This endpoint does not have a request body.

### Request Example
```python
from google.ads.googleads.client import GoogleAdsClient

# Load client from configuration file
client = GoogleAdsClient.load_from_storage("path/to/google-ads.yaml")

# Define customer ID
customer_id = "YOUR_CUSTOMER_ID"

# Get Google Ads service client
ga_service = client.get_service("GoogleAdsService")

# Define the query to retrieve campaigns
query = """
    SELECT
      campaign.id,
      campaign.name
    FROM campaign
    ORDER BY campaign.id"""

# Issue a search request using streaming
stream = ga_service.search_stream(customer_id=customer_id, query=query)

# Process the stream of results
for batch in stream:
    rows = batch.results
    for row in rows:
        print(
            f"Campaign with ID {row.campaign.id} and name "
            f'"{row.campaign.name}" was found.'
        )
```

### Response
#### Success Response (200)
- **campaign.id** (integer) - The ID of the campaign.
- **campaign.name** (string) - The name of the campaign.

#### Response Example
```json
{
  "results": [
    {
      "campaign": {
        "id": 1234567890,
        "name": "Example Campaign"
      }
    }
  ]
}
```
```

--------------------------------

### Java Client Library Setup and Campaign Retrieval

Source: https://developers.google.com/google-ads/api/docs/first-call/get-campaigns

Instructions for setting up the Java client library for Google Ads, including Maven dependencies, configuration, and an example of retrieving campaigns using `GoogleAdsService.SearchStream`.

```APIDOC
## Java Client Library

### Description
This section details how to set up and use the Google Ads API Java client library to retrieve campaign information.

### Maven Dependency
Add the following to your project's `pom.xml`:
```xml
<dependency>
  <groupId>com.google.api-ads</groupId>
  <artifactId>google-ads</artifactId>
  <version>40.0.0</version>
</dependency>
```

### Gradle Dependency
Add the following to your project's `build.gradle`:
```groovy
implementation 'com.google.api-ads:google-ads:40.0.0'
```

### Configuration
Create a `~/ads.properties` file with the following content:
```properties
api.googleads.serviceAccountSecretsPath=JSON_KEY_FILE_PATH
api.googleads.developerToken=INSERT_DEVELOPER_TOKEN_HERE
api.googleads.loginCustomerId=INSERT_LOGIN_CUSTOMER_ID_HERE
```

### Initialize GoogleAdsClient
```java
GoogleAdsClient googleAdsClient = null;
try {
  googleAdsClient = GoogleAdsClient.newBuilder().fromPropertiesFile().build();
} catch (FileNotFoundException fnfe) {
  System.err.printf("Failed to load GoogleAdsClient configuration from file. Exception: %s%n", fnfe);
  System.exit(1);
} catch (IOException ioe) {
  System.err.printf("Failed to create GoogleAdsClient. Exception: %s%n", ioe);
  System.exit(1);
}
```

### Retrieve Campaigns
```java
private void runExample(GoogleAdsClient googleAdsClient, long customerId) {
  try (GoogleAdsServiceClient googleAdsServiceClient = 
      googleAdsClient.getLatestVersion().createGoogleAdsServiceClient()) {
    String query = "SELECT campaign.id, campaign.name FROM campaign ORDER BY campaign.id";
    // Constructs the SearchGoogleAdsStreamRequest.
    SearchGoogleAdsStreamRequest request = 
        SearchGoogleAdsStreamRequest.newBuilder()
            .setCustomerId(Long.toString(customerId))
            .setQuery(query)
            .build();

    // Creates and issues a search Google Ads stream request that will retrieve all campaigns.
    ServerStream<SearchGoogleAdsStreamResponse> stream = 
        googleAdsServiceClient.searchStreamCallable().call(request);

    // Iterates through and prints all of the results in the stream response.
    for (SearchGoogleAdsStreamResponse response : stream) {
      for (GoogleAdsRow googleAdsRow : response.getResultsList()) {
        System.out.printf(
            "Campaign with ID %d and name '%s' was found.%n", 
            googleAdsRow.getCampaign().getId(), googleAdsRow.getCampaign().getName());
      }
    }
  }
}
```
```pleas