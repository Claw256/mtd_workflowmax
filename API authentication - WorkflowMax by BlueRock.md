## Before you get started

Before you can start using OAuth with , you will need to have:

-   a developer/user account
-   a developer application – this can be created [here](https://developer.workflowmax2.com/)
-   an account to integrate with your developer application.\*

_\*You must have full access to the “Authorize 3rd Party Full Access” privilege to integrate with a account._

## How it works

supports the [OAuth 2.0 Authorization Code grant type](https://developer.okta.com/blog/2018/04/10/oauth-authorization-code-grant-type), which can be broken down into five basic steps:

1.  Your application opens a browser window to send the user to the OAuth 2.0 server.
2.  The user reviews the requested permissions and grants the application access.
3.  The user is redirected back to the application with an authorization code in the query string.
4.  The application sends a request to the OAuth 2.0 server to exchange the authorization code for an access token.
5.  Make calls against the API.

## Getting OAuth 2.0 tokens

### Step 1: Create the authorization URL and direct the user to 's OAuth 2.0 server

When sending a user to 's OAuth 2.0 server, the first step is creating the authorization URL. This will identify your application and define the resources (scopes) it's requesting access to on behalf of the user. 

Your application should direct users to the following URL:   
_https://oauth.workflowmax2.com/oauth/authorize?response\_type=code&client\_id={YOURCLIENTID}&redirect\_uri={YOURREDIRECTURI}&scope= openid profile email workflowmax offline\_access&state={YOURSTATE}&prompt=consent_

The following values should be passed in as parameters:

<table><tbody><tr><td>response_type</td><td>code</td></tr><tr><td>client_id</td><td>Issued when you created your developer application</td></tr><tr><td>scope</td><td>Permissions to define the data that this application will access&nbsp;<br>openid email profile workflowmax offline_access</td></tr><tr><td>redirect_uri</td><td>The URL on the server to redirect back to (this must be HTTPS)</td></tr><tr><td><em>state</em></td><td><em>random string you can generate to prevent XSRF</em></td></tr><tr><td>prompt</td><td>consent</td></tr></tbody></table>

_Optional parameter - does not have to be included but it is recommended for security purposes_

###   
Step 2: Prompts user for consent

displays a consent window to the user showing the name of your application and a short description of the API services it's requesting permission to access. The user can then grant access to your app.

If any errors occur or the user denies the request, we redirect back to your redirect\_uri with an error parameter.

Your application doesn't do anything at this stage. Once access is granted, the OAuth 2.0 server will send a request to the callback URI defined in the authorization URL.

### Step 3: Handle the OAuth 2.0 server response

When the user has completed the consent prompt from Step 2, the OAuth 2.0 server sends a GET request to the redirect URI specified in your authentication URL. If there are no issues and the user approves the access request, the request to the redirect URI will be returned with a code query parameter attached.

If the user doesn't grant access, the request to the redirect URI will be returned with a query parameter: 

<table><tbody><tr><td>error</td><td>access_denied</td></tr><tr><td>error_description</td><td>The resource owner or authorization server denied the request</td></tr></tbody></table>

###   
Step 4: Exchange authorization code for tokens

After your application receives an authorization code from the OAuth 2.0 server, it can exchange that code for an access and refresh token.

To do this you will need to make a POST request to our token endpoint:

_https://oauth.workflowmax2.com/oauth/token_

The request body will need to contain the following:

<table><tbody><tr><td><p>grant_type</p></td><td>authorization_code</td></tr><tr><td>code</td><td>The authorization code you received in the callback</td></tr><tr><td>redirect_uri</td><td>The same redirect URI that was used when requesting the code</td></tr><tr><td>client_id</td><td>The app Client ID</td></tr><tr><td>client_secret</td><td>The app’s Client Secret</td></tr></tbody></table>

Please note this is different to the WorkflowMax by Xero API, which passes this information via headers.

The token endpoint will verify all the parameters in the request, ensuring the code hasn’t expired and that the client ID and secret match.

It will contain the following parameters:

<table><tbody><tr><td>access_token</td><td>The token used to call the API.</td></tr><tr><td>expires_in&nbsp;</td><td>The amount of seconds until the access token expires.</td></tr><tr><td>token_type</td><td>Type of the token returned&nbsp;<br>Bearer</td></tr><tr><td>refresh_token</td><td>The token used to refresh the access token once it has expired (only returned if the offline_access scope is requested).</td></tr></tbody></table>

All tokens received have an associated expiry time. Access tokens and refresh tokens can be exchanged prior to expiry.

Token expiry times:

-   access\_token: 30 minutes
-   refresh\_token: 60 days.

The access token is a JWT, which can be [decoded](https://jwt.io/) to retrieve the authentication organisation's Org ID, which will be required to make API calls (step 5). If your JWT does not contain an Organisation ID, please check that you have completed step 4 correctly by passing the parameters in the body (not as headers).

### Step 5: Call the API

Make calls against the API by simply adding the following headers to your request:

<table><tbody><tr><td>authorization</td><td>"Bearer " + access_token</td></tr><tr><td>account_id</td><td><span></span>organisation ID</td></tr></tbody></table>

To view the API contract documentation, please click [here](https://app.swaggerhub.com/apis/WorkflowMax-BlueRock/WorkflowMax-BlueRock-OpenAPI3/0.1).

## Refreshing access and refresh tokens

Access tokens expire after 30 minutes. Your application can refresh an access token without user interaction by using a refresh token. You get a refresh token by requesting the offline\_access scope during the initial user authorization. Refresh tokens expire after 60 days.

To refresh your access token you need to POST to the token endpoint:

_https://oauth.workflowmax2.com/oauth/token_

The request will require an authorization header containing your app’s client\_id and client\_secret

The request body will need to contain the grant type and refresh token.

<table><tbody><tr><td>grant_type</td><td>refresh_token</td></tr><tr><td>refresh_token</td><td>Your refresh token</td></tr><tr><td>client_id</td><td>The app Client ID</td></tr><tr><td>client_secret</td><td>The app’s Client Secret</td></tr><tr><td>scope</td><td>Same scope used</td></tr></tbody></table>

The response will contain a new access token and refresh token. You must save both tokens in order to maintain API access.