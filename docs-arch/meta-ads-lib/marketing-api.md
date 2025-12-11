### Conversions API Gateway - Setup Guide

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/guides/gateway/troubleshooting

A step-by-step guide on how to set up the Conversions API Gateway.

```APIDOC
## Conversions API Gateway - Setup Guide

### Description
This guide provides detailed instructions for setting up the Conversions API Gateway to manage your event data.

### Method
N/A

### Endpoint
N/A

### Parameters
N/A

### Request Example
N/A

### Response
N/A
```

--------------------------------

### Conversions API Overview

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/parameters/server-event

This section provides an overview of the Conversions API, including how to get started, use the API, and verify your setup.

```APIDOC
## Conversions API

### Description

The Conversions API allows businesses to send website and offline event data directly from their servers to Facebook, offering more control and reliability than browser-based tracking.

### Key Sections

*   **Get Started**: Initial setup and integration steps.
*   **Using the API**: Core concepts and workflow for sending events.
*   **Verifying Setup**: Tools and methods to confirm data is being received correctly.
*   **Parameters**: Detailed documentation for all available event parameters, categorized for clarity (Main Body, Server Event, Customer Information, Standard, App Data, Original Event Data).
*   **Parameter Builder Library**: Resources for constructing event payloads.
*   **Specific Use Cases**: Guides for App Events, Offline Events, Business Messaging, and Conversion Leads.
*   **Dataset Quality API**: For monitoring event quality.
*   **Handling Duplicate Events**: Strategies to avoid sending duplicate data.
*   **Guides**: Best practices and advanced topics.
*   **Troubleshooting**: Common issues and solutions.
```

--------------------------------

### Get Started with Real Estate Ads

Source: https://developers.facebook.com/docs/marketing-api/dynamic-ads-for-real-estate

A step-by-step guide on how to begin using the Real Estate Ads API.

```APIDOC
## Get Started with Real Estate Ads

### Description
This section outlines the necessary steps to get started with Facebook's Real Estate Ads API, including catalog setup and initial campaign creation.

### Steps
1. **Set up a Real Estate Catalog:** Ensure you have an appropriate catalog listing properties (apartments, condos, homes, land, etc.).
2. **Update Catalogs:** Learn how to regularly update your property listings using batch uploads or partial uploads.
3. **Adhere to Special Ad Category:** Specify `HOUSING` as the `special_ad_category` for housing ad campaigns.
4. **Create Ads:** Utilize the API to create customized ads that promote your listings.
```

--------------------------------

### Conversions API - Get Started

Source: https://developers.facebook.com/docs/marketing-api/facebook-pixel/server-side-api

Information on choosing an integration method, understanding prerequisites, and starting with the Conversions API.

```APIDOC
## Get Started

### Description
Choose the integration method that best suits your needs, review the prerequisites for using the Conversions API, and learn where to begin your implementation.

### Method
GET

### Endpoint
/vX.X/getting_started

### Parameters
None

### Request Example
None

### Response
#### Success Response (200)
- Documentation detailing integration options and prerequisites.

#### Response Example
None
```

--------------------------------

### Conversions API - Get Started

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/guides/gateway/troubleshooting

An introduction to the Conversions API and how to begin using it.

```APIDOC
## Conversions API - Get Started

### Description
This section provides an overview of the Facebook Conversions API and guides you through the initial steps to start sending conversion events.

### Method
N/A

### Endpoint
N/A

### Parameters
N/A

### Request Example
N/A

### Response
N/A
```

--------------------------------

### Conversions API Gateway - Getting Started

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/guides/gateway/troubleshooting

Provides an overview and initial steps for using the Conversions API Gateway.

```APIDOC
## Conversions API Gateway - Getting Started

### Description
This section details how to get started with the Conversions API Gateway, including its purpose and initial setup.

### Method
N/A

### Endpoint
N/A

### Parameters
N/A

### Request Example
N/A

### Response
N/A
```

--------------------------------

### Example JSON for Available Dates Price Config

Source: https://developers.facebook.com/docs/marketing-api/real-estate-ads/get-started

This JSON structure demonstrates how to provide the availability and prices of a property for specific date ranges. It includes start and end dates, rate, currency, and the interval (e.g., nightly, weekly, monthly).

```json
"available_dates_price_config": [
    {
        "end_date": "2018-11-01",
        "rate": "15000",
        "currency": "USD",
        "interval": "nightly"
    },
    {
        "start_date": "2018-11-01",
        "end_date": "2018-12-01",
        "rate": "20000",
        "currency": "USD",
        "interval": "nightly"
    },
    {
        "start_date": "2018-11-01",
        "rate": "50000",
        "currency": "USD",
        "interval": "weekly"
    }
]
```

--------------------------------

### Lead Ads Webhooks Setup

Source: https://developers.facebook.com/docs/marketing-api/guides/lead-ads/retrieving

This section outlines the steps to set up webhooks for real-time lead ad updates. It includes getting started, obtaining a long-lived page access token, and installing your app on the page.

```APIDOC
## Webhooks for Lead Ads

### Description
Configure real-time notifications for new leads submitted through Facebook Lead Ads.

### Method
N/A (This describes a configuration process, not a direct API call)

### Endpoint
N/A

### Steps
1.  **Get Started**: Visit the Webhooks Get Started guide to set up your endpoint and configure your webhook.
2.  **Get a Long-Lived Page Access Token**: Generate a single, long-lived Page token to continuously fetch data without worrying about it expiring.
3.  **Install Your App on the Page**: Visit the Webhooks for Pages guide to learn how to install your app on a Page.
```

--------------------------------

### Install Python SDK for Conversions API Parameter Builder

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/parameter-builder-feature-library/server-side-onboarding

This command installs the CAPI Parameter Builder Python library using pip. After installation, you can verify its presence by running 'pip list'.

```bash
pip install capi_param_builder_python
```

--------------------------------

### Install Ruby Gem for Conversions API Parameter Builder

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/parameter-builder-feature-library/server-side-onboarding

This command installs the CAPI Parameter Builder Ruby gem. Ensure your Ruby environment is set up correctly to install gems.

```bash
gem install capi_param_builder_ruby
```

--------------------------------

### Conversions API - Verifying Setup

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/guides/gateway-multiple-accounts

Guides on how to verify that your Conversions API implementation is set up correctly and events are being received by Meta.

```APIDOC
## Verifying Conversions API Setup

### Description
Ensuring your Conversions API implementation is working correctly is crucial. This section provides methods and tools to verify that events are being sent and received by Meta accurately.

### Verification Methods
*   **Test Events Tool:** Use the Test Events tool in Events Manager to send test events and see if they are received.
*   **Server Logs:** Check your server logs for successful API request confirmations.
*   **Events Manager Dashboard:** Monitor the dashboard for incoming events and potential errors.

### Troubleshooting
If you encounter issues, consult the 'Troubleshooting' section for common problems and solutions.
```

--------------------------------

### Preview Advantage+ Creative Feature

Source: https://developers.facebook.com/docs/marketing-api/creative/advantage-creative/get-started

This `curl` example demonstrates how to request a preview for a specific Advantage+ Creative feature using the Facebook Marketing API. It includes parameters for ad format, the desired creative feature, and an access token.

```shell
curl -X GET -G \
  -d 'ad_format="DESKTOP_FEED_STANDARD"' \
  -d 'creative_feature=<FEATURE_NAME> \
  -d 'access_token=<ACCESS_TOKEN>' \
https://graph.facebook.com/v24.0/<AD_ID>/previews
```

--------------------------------

### Adapting Ads to Placements with Facebook Marketing API

Source: https://developers.facebook.com/docs/marketing-api/creative/advantage-creative/get-started

This JSON example demonstrates how to enable the `adapt_to_placement` feature. By setting `adapt_to_placement.enroll_status` to `OPT_IN`, 9:16 images from your catalog will be displayed in supported placements like Instagram Stories and Reels.

```JSON
{
    "creative_features_spec": {
        "adapt_to_placement": {
            "enroll_status": "OPT_IN"
        }
    }
}
```

--------------------------------

### Preview Advantage+ Creative Ad Response

Source: https://developers.facebook.com/docs/marketing-api/creative/advantage-creative/get-started

This JSON structure represents an example response for previewing an ad creative with Advantage+ Creative features. It includes the body of the ad, and within `transformation_spec`, it details which features are eligible for the given placement.

```json
{
  "data": [
    {
      "body": "<iframe src='<PREVIEW_URL>'></iframe>",
      "transformation_spec": {
        "<FEATURE_NAME>": [
          {
            "body": "<iframe src='<PREVIEW_URL>'></iframe>",
            "status": "eligible"
          }
        ]
      }
    }
  ]
}
```

--------------------------------

### Implement eTLD+1 Resolver (Java)

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/parameter-builder-feature-library/server-side-onboarding

This Java example demonstrates a custom SimpleETLDPlusOneresolver implementing the ETLDPlusOneResolver interface, returning 'example.com' if the provided domain is a subdomain.

```java
// We provide DefaultETLDPlusOneResolver, which uses Guava InternetDomainName to resolve ETLD+1. If you prefer to do it yourself, follow the example below:

public class SimpleETLDPlusOneresolver implements ETLDPlusOneResolver {
	@Override
	public String resolve(String domain) {
               if (isSubdomain(domain, "example.com")) {
	       return "example.com"
               }
               // throw exception or fallback to other function
        }
}

```

--------------------------------

### Create AdCreative with Music Feature

Source: https://developers.facebook.com/docs/marketing-api/creative/advantage-creative/get-started

This `curl` example shows how to create an ad creative using the Facebook Marketing API, specifically opting into the 'Advantage+ Creative Music' feature by setting an audio type in the `asset_feed_spec`.

```shell
curl -X POST \
  -F 'name="Advantage+ Creative Music"' \
  -F 'object_story_spec={
       "page_id": "<PAGE_ID>"
     }' \
  -F 'asset_feed_spec={
       "audios": [
         {
           "type": "random"
         }
       ]
     }' \
  -F 'access_token=<ACCESS_TOKEN>' \
  https://graph.facebook.com/v24.0/act_<AD_ACCOUNT_ID>/adcreatives
```

--------------------------------

### Testing and Development Setup

Source: https://developers.facebook.com/docs/marketing-api/2tier-bm-solution/support

This guide outlines the steps to set up a testing environment for the Facebook Marketing APIs, including creating test users and obtaining access tokens.

```APIDOC
## Testing and Development Setup

### Description
This guide outlines the steps to set up a testing environment for the Facebook Marketing APIs. It covers creating test users, generating access tokens with the necessary permissions, and configuring test pages.

### Steps
1. **Log in to your app dashboard** at `https://developers.facebook.com/`. 
2. **Add a test user**: Navigate to your app's roles and click on "Add Test User". You can also add a test user for a specific Business Manager using the following URL structure: `https://developers.facebook.com/apps/app_id/roles/test-users/?business_id=bmid` (Replace `app_id` and `bmid` with your actual App ID and Business Manager ID).
3. **Generate an access token for the test user**: After creating the test user, click "Edit" for that user and then "Generate Access Token". Ensure you select the `business_management` and `ads_management` permissions. You may also need to grant standard tier access depending on the API features you are testing.
4. **Create or use an existing Facebook Page**: For testing purposes, create a new Facebook Page or use one that is already available.
5. **Add the test user as an admin to the test Page**: Go to the Page's settings (`https://www.facebook.com/page_id/settings/?tab=admin_roles`, replacing `page_id` with the actual Page ID) and assign the newly created test user the "Page Admin" role.
6. **Use the test user in API calls**: Now you can use the test user's generated access token in your API requests to interact with the Marketing APIs in a test environment.

### Important Notes
- Ensure your app is marked as a non-development app and has undergone App Review if you are testing features that require it.
- Without standard-tier access, certain Marketing API features may not be available for testing.
```

--------------------------------

### Real Estate Ads Overview

Source: https://developers.facebook.com/docs/marketing-api/real-estate-ads

Information on how to get started with real estate ads on Facebook, including catalog setup and usage.

```APIDOC
## Real Estate Ads

### Description
Use Facebook's real estate ads to leverage cross-device intent signals to automatically promote relevant listings from your inventory with a unique creative on Facebook. For Facebook Marketplace, use this list of our Marketplace listing partners and contact them to arrange for your inventory to be on Marketplace. (Currently, this feature is only available in certain countries.)

To use Facebook's real estate ads, you need an appropriate real estate catalog that lists properties (apartments, condos, homes, land, and so on) to advertise. Each property has information to create customized ads. You can regularly update catalogs through various options. If you use batch uploads, you can also use a partial upload option that enables you to create or update items that changed; see Batch Upload. This is available for all Advantage+ catalog ads.

### Documentation Contents

#### Get Started
A list of steps on how to get started with real estate ads.

#### Guides
Use case-based guides to help you perform specific actions.

#### Support
Solutions to common problems, troubleshooting tips, and FAQs.

### Special Ad Category
Advertisers must specify `HOUSING` as a `special_ad_category` for ad campaigns that market housing. In doing so, the set of targeting options available for ads in these campaigns will be restricted. Advantage+ catalog ads using Home Listing Catalogs must adhere to these restrictions. See Special Ad Category for more information.
```

--------------------------------

### Conversions API - Overview

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/guides/gateway-multiple-accounts

Provides an overview of the Conversions API, its purpose, and how to get started with implementing it for tracking conversions.

```APIDOC
## Conversions API

### Description
This API allows businesses to send web events directly from their servers to Meta, complementing the Meta Pixel and providing more control over data. It's essential for accurate conversion tracking and optimization of ad campaigns.

### Key Features
*   **Reliable Event Tracking:** Send events directly from your server.
*   **Data Control:** More control over the data sent to Meta.
*   **Improved Accuracy:** Complement the Meta Pixel for more robust tracking.

### Getting Started
Refer to the 'Get Started' section for initial setup and integration steps.
```

--------------------------------

### Opt-in to Advantage+ Creative Features via API

Source: https://developers.facebook.com/docs/marketing-api/creative/advantage-creative/get-started

This example demonstrates how to opt-in to specific Advantage+ Creative features like image touchups, inline comments, and image templates when creating an ad creative or an ad using the Facebook Marketing API. It requires specifying the desired features within the `creative_features_spec` object.

```curl
curl -X POST \
  -F 'name=Advantage+ Creative Creative' \
  -F 'degrees_of_freedom_spec={
    "creative_features_spec": {
      "image_touchups": {
        "enroll_status": "OPT_IN"
      },
     "inline_comment": {
        "enroll_status": "OPT_IN"
      },
     "image_template": {
        "enroll_status": "OPT_IN"
      }
    }
  }' \
  -F 'access_token=<ACCESS_TOKEN>' \
  https://graph.facebook.com/v24.0/act_<AD_ACCOUNT_ID>/adcreatives
```

```curl
curl -X POST \
  -F 'adset_id=<ADSET_ID>' \
  -F 'creative={
    "name": "Advantage+ Creative Adgroup",
    "object_story_spec": {
      "link_data": {
         "image_hash": "<IMAGE_HASH>", 
         "link": "<URL>", 
         "message": "You got this.",
      },
      "page_id": "<PAGE_ID>"
    },
    "degrees_of_freedom_spec": {
      "creative_features_spec": {
        "image_touchups": {
          "enroll_status": "OPT_IN"
        },
       "inline_comment": {
          "enroll_status": "OPT_IN"
        },
       "image_template": {
          "enroll_status": "OPT_IN"
        }
      }
    }
  }' \
https://graph.facebook.com/v24.0/act_<AD_ACCOUNT_ID>/ads
```

--------------------------------

### Advantage+ Catalog Ads - Direct Upload

Source: https://developers.facebook.com/docs/marketing-api/real-estate-ads/get-started

Manually perform a one-time upload of a product feed for Advantage+ catalog ads.

```APIDOC
## Advantage+ Catalog Ads - Direct Upload

### Description
Manually perform a one-time upload of a product feed for Advantage+ catalog ads.

### Method
POST

### Endpoint
`https://graph.facebook.com/<API_VERSION>/<PRODUCT_FEED_ID>/uploads`

### Parameters
#### Request Body
- **url** (string) - Required - URL of the product feed file.
- **access_token** (string) - Required - Your API access token.

### Request Example
```bash
curl \
  -F "url=http://www.example.com/sample_feed.xml" \
  -F "access_token=<ACCESS_TOKEN>" \
  https://graph.facebook.com/<API_VERSION>/<PRODUCT_FEED_ID>/uploads
```
```

--------------------------------

### Correct Product Variant Setup Example

Source: https://developers.facebook.com/docs/marketing-api/catalog/product-variants

This example illustrates the correct method for setting up product variants. It shows how the 'item_group_id' unifies variants, and each product has its specific attributes while sharing a common identifier for grouping.

```text
ID | Name | Color | Price | item_group_id
---|---|---|---|---
CoolShirt123_red | Cool Shirt | red | $9.99 | CoolShirt123
CoolShirt123_blue | Cool Shirt | blue | $9.99 | CoolShirt123
```

--------------------------------

### App Install Event Payload Structure

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/app-events

Example of the data structure for an 'Install' event payload in the Conversions API.

```APIDOC
## POST /conversions/v1/events

### Description
This endpoint allows you to send app install events to the Conversions API. The payload includes detailed information about the event, user, and application.

### Method
POST

### Endpoint
`/conversions/v1/events`

### Parameters
#### Request Body
- **data** (array) - Required - An array containing event objects.
  - **event_name** (string) - Required - The name of the event (e.g., "MobileAppInstall").
  - **event_time** (integer) - Required - The time the event occurred, in Unix timestamp format.
  - **action_source** (string) - Required - The source of the action (e.g., "app").
  - **user_data** (object) - Required - Information about the user.
    - **client_ip_address** (string) - Optional - The IP address of the client.
    - **madid** (string) - Optional - The Mobile Advertising ID.
    - **anon_id** (string) - Optional - An anonymous ID for the user.
  - **app_data** (object) - Optional - Information about the application.
    - **advertiser_tracking_enabled** (integer) - Optional - Indicates if advertiser tracking is enabled (1 for enabled, 0 for disabled).
    - **application_tracking_enabled** (integer) - Optional - Indicates if application tracking is enabled (1 for enabled, 0 for disabled).
    - **extinfo** (array) - Optional - Extended information about the app, device, and locale.

### Request Example
```json
{
  "data": [
    {
      "event_name": "MobileAppInstall",
      "event_time": 1684389252,
      "action_source": "app",
      "user_data": {
        "client_ip_address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        "madid": "38400000-8cf0-11bd-b23e-10b96e40000d",
        "anon_id": "12345340-1234-3456-1234-123456789012"
      },
      "app_data": {
        "advertiser_tracking_enabled": 1,
        "application_tracking_enabled": 1,
        "extinfo": [
          "a2",
          "com.some.app",
          "771",
          "Version 7.7.1",
          "10.1.1",
          "OnePlus6",
          "en_US",
          "GMT-1",
          "TMobile",
          "1920",
          "1080",
          "2.00",
          "2",
          "128",
          "8",
          "USA/New York"
        ]
      }
    }
  ]
}
```

### Response
#### Success Response (200)
- **success** (boolean) - Indicates if the event was processed successfully.
- **message** (string) - A message describing the outcome of the event processing.

#### Response Example
```json
{
  "success": true,
  "message": "Event processed successfully."
}
```
```

--------------------------------

### Enhancing CTA with AI-Suggested Phrases via API

Source: https://developers.facebook.com/docs/marketing-api/creative/advantage-creative/get-started

This JSON example demonstrates how to opt-in to the `enhance_cta` feature. By setting `enhance_cta.enroll_status` to `OPT_IN` and potentially providing AI-identified high-performing phrases in the `customizations.text_extraction` field, the API will pair relevant keyphrases with your Call to Action.

```JSON
{
    "creative_features_spec": {
        "enhance_cta": {
            "enroll_status": "OPT_IN",
            "customizations": {
                "text_extraction": {
                    "enroll_status": "OPT_IN"
                }
            }
        }
    }
}
```

--------------------------------

### Implement eTLD+1 Resolver (PHP)

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/parameter-builder-feature-library/server-side-onboarding

This PHP example shows a custom implementation of the ETLDPlus1Resolver interface, specifically for resolving 'example.com' as the eTLD+1 if the domain is a subdomain of it.

```php
class SimpleETLDPlus1Resolver implements ETLDPlus1Resolver {
   public function resolveETLDPlus1($domain) {
       if (isSubdomain($domain, "example.com")) {
           return "example.com";
       }
       throw new InvalidArgumentException("only example.com is supported");
   }
}

```

--------------------------------

### Create Home Listing Catalog

Source: https://developers.facebook.com/docs/marketing-api/real-estate-ads/get-started

This endpoint allows you to create a product catalog specifically for home listings, which is a prerequisite for running Advantage+ Catalog Ads for real estate.

```APIDOC
## POST /<API_VERSION>/<BUSINESS_ID>/owned_product_catalogs

### Description
Creates a product catalog with the `home_listings` vertical for advertising real estate properties.

### Method
POST

### Endpoint
`https://graph.facebook.com/<API_VERSION>/<BUSINESS_ID>/owned_product_catalogs`

### Parameters
#### Path Parameters
- **API_VERSION** (string) - Required - The version of the Marketing API.
- **BUSINESS_ID** (string) - Required - The ID of the business account.

#### Form Data Parameters
- **name** (string) - Required - The name of the catalog.
- **vertical** (string) - Required - Must be set to `home_listings`.
- **access_token** (string) - Required - Your valid Marketing API access token.

### Request Example
```bash
curl \
  -F 'name=Home Listing Catalog Name' \
  -F 'vertical=home_listings' \
  -F 'access_token=<ACCESS TOKEN>' \
  https://graph.facebook.com/<API_VERSION>/<BUSINESS_ID>/owned_product_catalogs
```

### Response
#### Success Response (200)
- **id** (string) - The ID of the newly created catalog.

#### Response Example
```json
{
  "id": "<CATALOG_ID>"
}
```
```

--------------------------------

### Create Ad Set - App Installs (Curl)

Source: https://developers.facebook.com/docs/marketing-api/adset

This example demonstrates how to create an ad set for app installs using a cURL command. It specifies daily budget, bid amount, optimization goal, campaign details, targeting, status, and access token. Ensure you replace placeholder values with your actual IDs and tokens.

```curl
curl -X POST \
  -F 'name="Mobile App Installs Ad Set"' \
  -F 'daily_budget=1000' \
  -F 'bid_amount=2' \
  -F 'billing_event="IMPRESSIONS"' \
  -F 'optimization_goal="APP_INSTALLS"' \
  -F 'campaign_id="<AD_CAMPAIGN_ID>"' \
  -F 'promoted_object={
       "application_id": "<APP_ID>",
       "object_store_url": "<APP_STORE_URL>"
     }' \
  -F 'targeting={
       "device_platforms": [
         "mobile"
       ],
       "facebook_positions": [
         "feed"
       ],
       "geo_locations": {
         "countries": [
           "US"
         ]
       },
       "publisher_platforms": [
         "facebook",
         "audience_network"
       ],
       "user_os": [
         "IOS"
       ]
     }' \
  -F 'status="PAUSED"' \
  -F 'access_token=<ACCESS_TOKEN>' \
https://graph.facebook.com/v24.0/act_<AD_ACCOUNT_ID>/adsets
```

--------------------------------

### Conversions API Gateway - Post-Setup Management

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/guides/gateway/troubleshooting

Information on managing the Conversions API Gateway after initial setup.

```APIDOC
## Conversions API Gateway - Post-Setup Management

### Description
This section covers the ongoing management and maintenance of the Conversions API Gateway after it has been set up.

### Method
N/A

### Endpoint
N/A

### Parameters
N/A

### Request Example
N/A

### Response
N/A
```

--------------------------------

### Async Examples

Source: https://developers.facebook.com/docs/marketing-api/batch-requests

Provides various examples for interacting with asynchronous requests, including getting the status of a specific request, retrieving request results, listing request sets for an ad account, and getting a list of requests for a campaign.

```APIDOC
## Async Examples

### Get Status of a Specific Async Request

#### Method
GET

#### Endpoint
`https://graph.facebook.com/v24.0/`

#### Query Parameters
- **id** (string) - Required - The ID of the async request.
- **pretty** (boolean) - Optional - Set to `true` for command-line readable output.
- **access_token** (string) - Required - Your Facebook API access token.

#### Request Example
```bash
curl -G \
-d "id=6012384857989" \
-d "pretty=true" \
-d "access_token=_____" \
"https://graph.facebook.com/v24.0/"
```

#### Response Example
```json
{
   "id": "6012384857989",
   "owner_id": 12345,
   "name": "testasyncset",
   "is_completed": true
}
```

### Get Results of Requests

#### Method
GET

#### Endpoint
`https://graph.facebook.com/v24.0/requests`

#### Query Parameters
- **id** (string) - Required - The ID of the request to get results for.
- **pretty** (boolean) - Optional - Set to `true` for command-line readable output.
- **fields** (string) - Optional - Specifies the fields to return, include `result` to get the results.
- **access_token** (string) - Required - Your Facebook API access token.

#### Request Example
```bash
curl -G \
-d "id=6012384857989" \
-d "pretty=true" \
-d "fields=result" \
-d "access_token=_____" \
"https://graph.facebook.com/v24.0/requests"
```

#### Response Example
```json
{
   "data": [
      {
         "result": {
            "id": "6012384860989"
         },
         "id": "6012384858389"
      },
      {
         "result": {
            "id": "6012384858789"
         },
         "id": "6012384858189"
      }
   ],
   "paging": {
      "cursors": {
         "after": "___",
         "before": "__-"
      }
   }
}
```

### Get List of Request Sets for an Ad Account

#### Method
GET

#### Endpoint
`https://graph.facebook.com/v24.0/act_<AD_ACCOUNT_ID>/asyncadrequestsets`

#### Query Parameters
- **is_completed** (integer) - Optional - Filter by completion status (e.g., `1` for completed).
- **pretty** (boolean) - Optional - Set to `true` for command-line readable output.
- **access_token** (string) - Required - Your Facebook API access token.

#### Request Example
```bash
curl -G \
-d "is_completed=1" \
-d "pretty=true" \
-d "access_token=___" \
"https://graph.facebook.com/v24.0/act_71597454/asyncadrequestsets"
```

#### Response Example
```json
{
   "data": [
      {
         "id": "6012384253789",
         "owner_id": 71597454,
         "name": "testasyncset",
         "is_completed": true
      },
   ],
   "paging": {
      "cursors": {
         "after": "__-",
         "before": "__-"
      }
   }
}
```

### Get List of Requests for a Campaign

#### Method
GET

#### Endpoint
`https://graph.facebook.com/v24.0/<CAMPAIGN_ID>/asyncadrequests`

#### Query Parameters
- **status** (string) - Optional - Filter by request status (e.g., `SUCCESS`, `ERROR`).
- **pretty** (boolean) - Optional - Set to `true` for command-line readable output.
- **access_token** (string) - Required - Your Facebook API access token.

#### Request Example
```bash
curl -G \
-d "status=SUCCESS,ERROR" \
-d "pretty=true" \
-d "access_token=___" \
"https://graph.facebook.com/v24.0/6008248529789/asyncadrequests"
```

#### Response Example
```json
{
   "data": [
      {
         "id": "6012384951789",
         "scope_object_id": 6008248529789,
         "status": "SUCCESS"
      },
   ],
   "paging": {
      "cursors": {
         "after": "__-",
         "before": "__-"
      }
   }
}
```
```

--------------------------------

### Migration Example: Java

Source: https://developers.facebook.com/docs/marketing-api/facebook-pixel/server-side-api/using-the-api

Example demonstrating how to integrate `CAPIGatewayIngressRequest` into an existing Java Business SDK setup.

```APIDOC
## Migration Example: Java

### Description
This example shows how to reference and attach the `CAPIGatewayIngressRequest` to an `EventRequest`'s custom endpoint in a Java environment.

### Method
Referencing and attaching `CAPIGatewayIngressRequest`

### Endpoint
N/A

### Request Example
```java
// this is the standard event request that we attach events to
EventRequest eventRequest = new EventRequest(PIXEL_ID, context);
CAPIGatewayIngressRequest capiSyncRequest = new CAPIGatewayIngressRequest(CB_URL, CAPIG_ACCESS_KEY);
eventRequest.setCustomEndpoint(capiSyncRequest);
eventRequest.addDataItem(testEvent);
eventRequest.execute();
```

### Response
#### Success Response (200)
This operation processes events and does not return a specific response body at this stage.

#### Response Example
N/A
```

--------------------------------

### Ad Previews API

Source: https://developers.facebook.com/docs/marketing-api/generatepreview/v17

This section of the Facebook Marketing API allows developers to generate previews of ads. It includes details on how to get started, provides examples, and specifies the API version.

```APIDOC
## Ad Previews

### Description
This API endpoint allows you to generate previews of your ads to see how they will appear on Facebook platforms.

### Method
GET

### Endpoint
/v24.0/ads_preview

### Parameters
#### Query Parameters
- **ad_id** (string) - Required - The ID of the ad to preview.
- **platform** (string) - Optional - The platform where the ad will be displayed (e.g., `facebook`, `instagram`).

### Request Example
```json
{
  "ad_id": "YOUR_AD_ID",
  "platform": "facebook"
}
```

### Response
#### Success Response (200)
- **preview_url** (string) - The URL where the ad preview can be viewed.

#### Response Example
```json
{
  "preview_url": "https://www.facebook.com/ads/preview/YOUR_PREVIEW_ID"
}
```
```

--------------------------------

### Implement eTLD+1 Resolver (Node.js)

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/parameter-builder-feature-library/server-side-onboarding

This Node.js snippet provides an example of a custom SimpleETLDPlus1Resolver class that checks if a domain is a subdomain of 'example.com' and returns 'example.com' if it is.

```javascript
/*
//Currently we provide 3 options; you may also implement your own resolver.

1. [Recommended] Resolve etld+1 by default
     const etldPlus1Resolver = new DefaultETLDPlus1Resolver();
2. Resolve by half manual input
     const etldPlus1Resolver = new DefaultETLDPlus1Resolver('www.example.com'); // => 'example.com';
3. Manual identify etld+1 (mostly for localhost test).
     const etldPlus1Resolver = new DummyLocalHostTestResolver('localhost');
4. Implement a new resolver by yourself. Example below:

*/
    
class SimpleETLDPlus1Resolver {
   resolveETLDPlus1(domain) {
	if (isSubdomain(domain, "example.com")) {
	return "example.com";
}
      // throw exception or fallback to other functions
   }

```

--------------------------------

### POST /<CATALOG_ID>/product_sets

Source: https://developers.facebook.com/docs/marketing-api/real-estate-ads/get-started

Creates a product set for a catalog with specified filters. This is used to group items for advertising.

```APIDOC
## POST /<CATALOG_ID>/product_sets

### Description
Creates a product set within a specific catalog, which can be used to define a group of items for Advantage+ catalog ads. Filters can be applied to determine which items are included in the set.

### Method
POST

### Endpoint
`https://graph.facebook.com/<API_VERSION>/<CATALOG_ID>/product_sets`

### Parameters
#### Path Parameters
- **API_VERSION** (string) - Required - The version of the Facebook Graph API.
- **CATALOG_ID** (string) - Required - The ID of the catalog to create the product set in.

#### Query Parameters
- **access_token** (string) - Required - Your Facebook API access token.

#### Request Body
- **name** (string) - Required - The name of the product set.
- **filter** (JSON object) - Required - A JSON object defining the filters for the product set. See "Filter Operators and Data" below for details.

### Filter Operators and Data
Operators:
- `i_contains`: Contains substring (case insensitive)
- `i_not_contains`: Does not contain substring (case insensitive)
- `contains`: Contains substring (case sensitive)
- `not_contains`: Does not contain substring (case sensitive)
- `eq`: Equal to (case insensitive)
- `neq`: Not equal to (case insensitive)
- `lt`: Less than (numeric fields only)
- `lte`: Less than or equal to (numeric fields only)
- `gt`: Greater than (numeric fields only)
- `gte`: Greater than or equal to (numeric fields only)

Data:
- `availability` (string) - Listing availability (e.g., `for_sale`).
- `listing_type` (string) - Listing type (e.g., `for_sale_by_agent`).
- `property_type` (string) - Property type (e.g., `house`).
- `price` (number) - Listing price.
- `name` (string) - Name of the listing.
- `city` (string) - City of the listing.
- `country` (string) - Country of the listing.
- `region` (string) - Region or state of the listing.
- `postal_code` (string) - Postal code of the listing.
- `num_beds` (number) - Number of beds.
- `num_baths` (number) - Number of baths.

### Request Example
```json
{
  "name": "test set",
  "filter": {
    "availability": {
      "eq": "for_sale"
    }
  },
  "access_token": "<YOUR_ACCESS_TOKEN>"
}
```

### Response
#### Success Response (200)
- **id** (string) - The ID of the created product set.
- **name** (string) - The name of the product set.

#### Response Example
```json
{
  "id": "1234567890",
  "name": "test set"
}
```
```

--------------------------------

### Conversions API - Verifying Setup

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/guides/gateway/troubleshooting

Steps to verify that your Conversions API implementation is set up correctly.

```APIDOC
## Conversions API - Verifying Setup

### Description
This section details the methods and tools available to verify that your Conversions API integration is working as expected and events are being received correctly.

### Method
N/A

### Endpoint
N/A

### Parameters
N/A

### Request Example
N/A

### Response
N/A
```

--------------------------------

### Configuring AI Image Overlays with Facebook Marketing API

Source: https://developers.facebook.com/docs/marketing-api/creative/advantage-creative/get-started

This code example shows how to enable AI-generated image overlays using the `creative_features_spec`. By setting `image_templates.enroll_status` to `OPT_IN`, the API will automatically add overlays with provided text to ad creatives when it's predicted to improve performance.

```JSON
{
    "creative_features_spec": {
        "image_templates": {
            "enroll_status": "OPT_IN"
        }
    }
}
```

--------------------------------

### Migration Example: PHP

Source: https://developers.facebook.com/docs/marketing-api/facebook-pixel/server-side-api/using-the-api

Example demonstrating how to integrate `CAPIGatewayIngressRequest` into an existing PHP Business SDK setup.

```APIDOC
## Migration Example: PHP

### Description
This example shows how to reference and attach the `CAPIGatewayIngressRequest` to an `EventRequest`'s custom endpoint in a PHP environment.

### Method
Referencing and attaching `CAPIGatewayIngressRequest`

### Endpoint
N/A

### Request Example
```php
// this is the standard event request that we attach events to
$event_request = new EventRequest($this->pixel_id);
$capiIngressRequest = new CAPIGatewayIngressRequest($this->cb_url, $this->access_key);
$event_request->setCustomEndpoint($capiIngressRequest);
// pass the events to this event Request object
$event_request->setEvents($events);
$event_request->execute();
```

### Response
#### Success Response (200)
This operation processes events and does not return a specific response body at this stage.

#### Response Example
N/A
```

--------------------------------

### Migration Example: Java

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/using-the-api

Provides an example of how to migrate existing systems using the Business SDK to utilize the CAPIGatewayIngressRequest.

```APIDOC
## Migration Example: Java

### Description
Demonstrates how to integrate CAPIGatewayIngressRequest into an existing Java Business SDK implementation.

### Request Example
```java
// this is the standard event request that we attach events to

EventRequest eventRequest = new EventRequest(PIXEL_ID, context);

CAPIGatewayIngressRequest capiSyncRequest = new CAPIGatewayIngressRequest(CB_URL, CAPIG_ACCESS_KEY);
eventRequest.setCustomEndpoint(capiSyncRequest);
eventRequest.addDataItem(testEvent);
eventRequest.execute();
```
```

--------------------------------

### Read Ad Account Reach Estimate (iOS SDK)

Source: https://developers.facebook.com/docs/marketing-api/reference/ad-account/reachestimate

This iOS SDK example illustrates how to get audience reach estimates using the Facebook SDK for Objective-C. It sets up parameters and starts a GraphRequest to the reachestimate endpoint.

```objectivec
NSDictionary *params = @{
  @"targeting_spec": @"{\"geo_locations\":{\"countries\":[\"US\"],\"age_min\":20,\"age_max\":40}"
};
/* make the API call */
FBSDKGraphRequest *request = [[FBSDKGraphRequest alloc]
                               initWithGraphPath:@"/act_<AD_ACCOUNT_ID>/reachestimate"
                                      parameters:params
                                      HTTPMethod:@"GET"];
[request startWithCompletionHandler:^(FBSDKGraphRequestConnection *connection,
                                      id result,
                                      NSError *error) {
    // Handle the result
}];

```

--------------------------------

### Python SDK Example for Creating Ad

Source: https://developers.facebook.com/docs/marketing-api/advantage-catalog-ads-for-leadgen

Example code using the Python Facebook Business SDK to create an ad.

```APIDOC
## Python SDK - Create Ad

### Description
This Python code snippet demonstrates how to create an ad using the Facebook Business SDK, linking it to a specific ad set and creative.

### Method
POST

### Endpoint
(Internal SDK method, corresponds to POST /act_<AD_ACCOUNT_ID>/ads)

### Parameters
- **access_token**: Your Facebook API access token.
- **app_secret**: Your Facebook App secret.
- **app_id**: Your Facebook App ID.
- **id**: The Ad Account ID.
- **params** (dict): A dictionary containing ad creation parameters:
  - **name** (str): The name of the ad.
  - **adset_id** (str): The ID of the ad set.
  - **creative** (dict): A dictionary with the `creative_id`.
  - **status** (str): The status of the ad (e.g., 'PAUSED').

### Request Example
```python
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.ad import Ad
from facebook_business.api import FacebookAdsApi

access_token = '<ACCESS_TOKEN>'
app_secret = '<APP_SECRET>'
app_id = '<APP_ID>'
id = '<AD_ACCOUNT_ID>'
FacebookAdsApi.init(access_token=access_token)

fields = [
]
params = {
  'name': 'My Ad',
  'adset_id': '<adSetID>',
  'creative': {'creative_id':'<adCreativeID>'},
  'status': 'PAUSED',
}

print(AdAccount(id).create_ad(
  fields=fields,
  params=params,
))
```
```

--------------------------------

### Migration Example: PHP

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/using-the-api

Provides an example of how to migrate existing systems using the Business SDK to utilize the CAPIGatewayIngressRequest.

```APIDOC
## Migration Example: PHP

### Description
Demonstrates how to integrate CAPIGatewayIngressRequest into an existing PHP Business SDK implementation.

### Request Example
```php
// this is the standard event request that we attach events to
$event_request = new EventRequest($this->pixel_id);
$capiIngressRequest = new CAPIGatewayIngressRequest($this->cb_url, $this->access_key);
$event_request->setCustomEndpoint($capiIngressRequest);
// pass the events to this event Request object
$event_request->setEvents($events);
$event_request->execute()
```
```

--------------------------------

### Set Ad Status to ACTIVE using Marketing API

Source: https://developers.facebook.com/docs/marketing-api/creative/advantage-creative/get-started

This example demonstrates how to set an ad's status to 'ACTIVE' using a cURL command. It requires the ad ID and an access token, and sends a POST request with the status parameter.

```bash
curl -X POST \
  -F 'status=ACTIVE' \
  -F 'access_token=<ACCESS_TOKEN>' \
  https://graph.facebook.com/v24.0/<AD_ID>
```

--------------------------------

### Conversions API Guides - End-to-end Implementation

Source: https://developers.facebook.com/docs/marketing-api/conversions-api/guides/gateway/troubleshooting

A guide detailing the end-to-end implementation process for the Conversions API.

```APIDOC
## Conversions API Guides - End-to-end Implementation

### Description
This guide walks you through the complete process of implementing the Conversions API, from initial setup to sending and verifying events.

### Method
N/A

### Endpoint
N/A

### Parameters
N/A

### Request Example
N/A

### Response
N/A
```

--------------------------------

### Ruby SDK Example for Creating Ad

Source: https://developers.facebook.com/docs/marketing-api/advantage-catalog-ads-for-leadgen

Example code using the Ruby Facebook Business SDK to create an ad.

```APIDOC
## Ruby SDK - Create Ad

### Description
This Ruby code snippet demonstrates how to create an ad using the Facebook Business SDK, linking it to a specific ad set and creative.

### Method
POST

### Endpoint
(Internal SDK method, corresponds to POST /act_<AD_ACCOUNT_ID>/ads)

### Parameters
- **access_token**: Your Facebook API access token.
- **app_secret**: Your Facebook App secret.
- **app_id**: Your Facebook App ID.
- **id**: The Ad Account ID.
- **config** (block): Block for configuring the FacebookAds gem.
- **ad_params** (hash): A hash containing ad creation parameters:
  - **name** (string): The name of the ad.
  - **adset_id** (string): The ID of the ad set.
  - **creative** (hash): A hash with the `creative_id`.
  - **status** (string): The status of the ad (e.g., 'PAUSED').

### Request Example
```ruby
require 'facebook_ads'

access_token = '<ACCESS_TOKEN>'
app_secret = '<APP_SECRET>'
app_id = '<APP_ID>'
id = '<AD_ACCOUNT_ID>'

FacebookAds.configure do |config|
  config.access_token = access_token
  config.app_secret = app_secret
end

ad_account = FacebookAds::AdAccount.get(id)
ads = ad_account.ads.create({
    name: 'My Ad',
    adset_id: '<ADSET_ID>',
    creative: {'creative_id':'<CREATIVE_ID>'},
    status: 'PAUSED',
})
```
```

--------------------------------

### Activating Video Auto-Cropping in Facebook Marketing API

Source: https://developers.facebook.com/docs/marketing-api/creative/advantage-creative/get-started

This example demonstrates how to enable automatic video cropping using the `video_auto_crop` feature. By setting `video_auto_crop.enroll_status` to `OPT_IN`, video ads will be automatically adjusted to fit different ad placements, ensuring optimal visibility.

```JSON
{
    "creative_features_spec": {
        "video_auto_crop": {
            "enroll_status": "OPT_IN"
        }
    }
}
```

--------------------------------

### Webhooks Setup - Callback URL Example

Source: https://developers.facebook.com/docs/marketing-api/ad-rules/guides/trigger-based-rules

An example of the data structure received at the callback URL when a rule is triggered. This structure includes information about the triggered rule and its associated object.

```APIDOC
## Webhooks Setup - Callback URL Example

### Description
This is an example of the data structure sent to your callback URL when a rule is triggered. It contains details about the event, including the rule ID, object ID, object type, and trigger information.

### Response Example
```json
{
  "object": "application",
  "entry": [{
    "id": "<APPLICATION_ID>",
    "time": 1468938744,
    "changes": [{
      "field": "ads_rules_engine",
      "value": {
        "rule_id": 1234,
        "object_id": 5678,
        "object_type": "ADSET",
        "trigger_type": "STATS_CHANGE",
        "trigger_field": "COST_PER_LINK_CLICK",
        "current_value": "15.8"
      }
    }]
  }]
}
```

### Notes
The `current_value` field is a JSON-encoded string and can represent a string, number, or an array.
```

--------------------------------

### Read Saved Audience (iOS SDK)

Source: https://developers.facebook.com/docs/marketing-api/reference/saved-audience

This iOS SDK example shows how to retrieve a Saved Audience using `FBSDKGraphRequest`. It initializes the request with the graph path and HTTP method (GET), then starts the request with a completion handler to manage the results and errors.

```Objective-C
/* make the API call */
FBSDKGraphRequest *request = [[FBSDKGraphRequest alloc]
                               initWithGraphPath:@"/{saved-audience-id}"
                                      parameters:params
                                      HTTPMethod:@"GET"];
[request startWithCompletionHandler:^(FBSDKGraphRequestConnection *connection,
                                      id result,
                                      NSError *error) {
    // Handle the result
}];
```