linkedin-api

_class_ linkedin\_api.Linkedin(_username: str_, _password: str_, _\*_, _authenticate\=True_, _refresh\_cookies\=False_, _debug\=False_, _proxies\={}_, _cookies\=None_, _cookies\_dir: str \= ''_)

Class for accessing the LinkedIn API.

Parameters:

-   **username** (_str_) – Username of LinkedIn account.
    
-   **password** (_str_) – Password of LinkedIn account.
    

add\_connection(_profile\_public\_id: str_, _message\=''_, _profile\_urn\=None_)

Add a given profile id as a connection.

Parameters:

-   **profile\_public\_id** (_str_) – public ID of a LinkedIn profile
    
-   **message** – message to send along with connection request
    
-   **profile\_urn** (_str__,_ _optional_) – member URN for the given LinkedIn profile
    

Returns:

Error state. True if error occurred

Return type:

boolean

follow\_company(_following\_state\_urn_, _following\=True_)

Follow a company from its ID.

Parameters:

-   **following\_state\_urn** (_str_) – LinkedIn State URN to append to URL to follow the company
    
-   **following** (_bool__,_ _optional_) – The following state to set. True by default for following the company
    

Returns:

Error state. If True, an error occured.

Return type:

boolean

get\_company(_public\_id_)

Fetch data about a given LinkedIn company.

Parameters:

**public\_id** (_str_) – LinkedIn public ID for a company

Returns:

Company data

Return type:

dict

get\_company\_updates(_public\_id: str | None \= None_, _urn\_id: str | None \= None_, _max\_results: int | None \= None_, _results: List | None \= None_) → List

Fetch company updates (news activity) for a given LinkedIn company.

Parameters:

-   **public\_id** (_str__,_ _optional_) – LinkedIn public ID for a company
    
-   **urn\_id** (_str__,_ _optional_) – LinkedIn URN ID for a company
    

Returns:

List of company update objects

Return type:

list

get\_conversation(_conversation\_urn\_id: str_)

Fetch data about a given conversation.

Parameters:

**conversation\_urn\_id** (_str_) – LinkedIn URN ID for a conversation

Returns:

Conversation data

Return type:

dict

get\_conversation\_details(_profile\_urn\_id_)

Fetch conversation (message thread) details for a given LinkedIn profile.

Parameters:

**profile\_urn\_id** (_str_) – LinkedIn URN ID for a profile

Returns:

Conversation data

Return type:

dict

get\_conversations()

Fetch list of conversations the user is in.

Returns:

List of conversations

Return type:

list

get\_current\_profile\_views()

Get profile view statistics, including chart data.

Returns:

Profile view data

Return type:

dict

get\_feed\_posts(_limit\=\-1_, _offset\=0_, _exclude\_promoted\_posts\=True_)

Get a list of URNs from feed sorted by ‘Recent’

Parameters:

-   **limit** (_int__,_ _optional_) – Maximum length of the returned list, defaults to -1 (no limit)
    
-   **offset** (_int__,_ _optional_) – Index to start searching from
    
-   **exclude\_promoted\_posts** (_bool__,_ _optional_) – Exclude from the output promoted posts
    

Returns:

List of URNs

Return type:

list

get\_invitations(_start\=0_, _limit\=3_)

Fetch connection invitations for the currently logged in user.

Parameters:

-   **start** (_int_) – How much to offset results by
    
-   **limit** (_int_) – Maximum amount of invitations to return
    

Returns:

List of invitation objects

Return type:

list

get\_job(_job\_id: str_) → Dict

Fetch data about a given job. :param job\_id: LinkedIn job ID :type job\_id: str

Returns:

Job data

Return type:

dict

get\_job\_skills(_job\_id: str_) → Dict

Fetch skills associated with a given job. :param job\_id: LinkedIn job ID :type job\_id: str

Returns:

Job skills

Return type:

dict

get\_post\_comments: Get post comments

Parameters:

-   **post\_urn** (_str_) – Post URN
    
-   **comment\_count** (_int__,_ _optional_) – Number of comments to fetch
    

Returns:

List of post comments

Return type:

list

get\_post\_reactions(_urn\_id_, _max\_results\=None_, _results\=None_)

Fetch social reactions for a given LinkedIn post.

Parameters:

-   **urn\_id** (_str_) – LinkedIn URN ID for a post
    
-   **max\_results** (_int__,_ _optional_) – Maximum results to return
    

Returns:

List of social reactions

Return type:

list

\# Note: This may need to be updated to GraphQL in the future, see [tomquirk/linkedin-api#309](https://github.com/tomquirk/linkedin-api/pull/309)

get\_profile(_public\_id: str | None \= None_, _urn\_id: str | None \= None_) → Dict

Fetch data for a given LinkedIn profile.

Parameters:

-   **public\_id** (_str__,_ _optional_) – LinkedIn public ID for a profile
    
-   **urn\_id** (_str__,_ _optional_) – LinkedIn URN ID for a profile
    

Returns:

Profile data

Return type:

dict

get\_profile\_connections(_urn\_id: str_, _\*\*kwargs_) → List

Fetch connections for a given LinkedIn profile.

See Linkedin.search\_people() for additional searching parameters.

Parameters:

**urn\_id** (_str_) – LinkedIn URN ID for a profile

Returns:

List of search results

Return type:

list

get\_profile\_contact\_info(_public\_id: str | None \= None_, _urn\_id: str | None \= None_) → Dict

Fetch contact information for a given LinkedIn profile. Pass a \[public\_id\] or a \[urn\_id\].

Parameters:

-   **public\_id** (_str__,_ _optional_) – LinkedIn public ID for a profile
    
-   **urn\_id** (_str__,_ _optional_) – LinkedIn URN ID for a profile
    

Returns:

Contact data

Return type:

dict

get\_profile\_experiences(_urn\_id: str_) → List

Fetch experiences for a given LinkedIn profile.

NOTE: data structure differs slightly from Linkedin.get\_profile() experiences.

Parameters:

**urn\_id** (_str_) – LinkedIn URN ID for a profile

Returns:

List of experiences

Return type:

list

get\_profile\_member\_badges(_public\_profile\_id: str_)

Fetch badges for a given LinkedIn profile.

Parameters:

**public\_profile\_id** (_str_) – public ID of a LinkedIn profile

Returns:

Badges data

Return type:

dict

get\_profile\_network\_info(_public\_profile\_id: str_)

Fetch network information for a given LinkedIn profile.

Network information includes the following: - number of connections - number of followers - if the account is followable - the network distance between the API session user and the profile - if the API session user is following the profile

Parameters:

**public\_profile\_id** (_str_) – public ID of a LinkedIn profile

Returns:

Network data

Return type:

dict

get\_profile\_posts(_public\_id: str | None \= None_, _urn\_id: str | None \= None_, _post\_count\=10_) → List

get\_profile\_posts: Get profile posts

Parameters:

-   **public\_id** (_str__,_ _optional_) – LinkedIn public ID for a profile
    
-   **urn\_id** (_str__,_ _optional_) – LinkedIn URN ID for a profile
    
-   **post\_count** (_int__,_ _optional_) – Number of posts to fetch
    

Returns:

List of posts

Return type:

list

get\_profile\_privacy\_settings(_public\_profile\_id: str_)

Fetch privacy settings for a given LinkedIn profile.

Parameters:

**public\_profile\_id** (_str_) – public ID of a LinkedIn profile

Returns:

Privacy settings data

Return type:

dict

get\_profile\_skills(_public\_id: str | None \= None_, _urn\_id: str | None \= None_) → List

Fetch the skills listed on a given LinkedIn profile.

Parameters:

-   **public\_id** (_str__,_ _optional_) – LinkedIn public ID for a profile
    
-   **urn\_id** (_str__,_ _optional_) – LinkedIn URN ID for a profile
    

Returns:

List of skill objects

Return type:

list

get\_profile\_updates(_public\_id\=None_, _urn\_id\=None_, _max\_results\=None_, _results\=None_)

Fetch profile updates (newsfeed activity) for a given LinkedIn profile.

Parameters:

-   **public\_id** (_str__,_ _optional_) – LinkedIn public ID for a profile
    
-   **urn\_id** (_str__,_ _optional_) – LinkedIn URN ID for a profile
    

Returns:

List of profile update objects

Return type:

list

get\_school(_public\_id_)

Fetch data about a given LinkedIn school.

Parameters:

**public\_id** (_str_) – LinkedIn public ID for a school

Returns:

School data

Return type:

dict

get\_user\_profile(_use\_cache\=True_) → Dict

Get the current user profile. If not cached, a network request will be fired.

Returns:

Profile data for currently logged in user

Return type:

dict

mark\_conversation\_as\_seen(_conversation\_urn\_id: str_)

Send ‘seen’ to a given conversation.

Parameters:

**conversation\_urn\_id** (_str_) – LinkedIn URN ID for a conversation

Returns:

Error state. If True, an error occured.

Return type:

boolean

react\_to\_post(_post\_urn\_id_, _reaction\_type\='LIKE'_)

React to a given post. :param post\_urn\_id: LinkedIn Post URN ID :type post\_urn\_id: str :param reactionType: LinkedIn reaction type, defaults to “LIKE”, can be “LIKE”, “PRAISE”, “APPRECIATION”, “EMPATHY”, “INTEREST”, “ENTERTAINMENT” :type reactionType: str

Returns:

Error state. If True, an error occured.

Return type:

boolean

remove\_connection(_public\_profile\_id: str_)

Remove a given profile as a connection.

Parameters:

**public\_profile\_id** (_str_) – public ID of a LinkedIn profile

Returns:

Error state. True if error occurred

Return type:

boolean

reply\_invitation(_invitation\_entity\_urn: str_, _invitation\_shared\_secret: str_, _action\='accept'_)

Respond to a connection invitation. By default, accept the invitation.

Parameters:

-   **invitation\_entity\_urn** (_int_) – URN ID of the invitation
    
-   **invitation\_shared\_secret** (_str_) – Shared secret of invitation
    
-   **action** (_str__,_ _optional_) – “accept” or “reject”. Defaults to “accept”
    

Returns:

Success state. True if successful

Return type:

boolean

search(_params: Dict_, _limit\=\-1_, _offset\=0_) → List

Perform a LinkedIn search.

Parameters:

-   **params** (_dict_) – Search parameters (see code)
    
-   **limit** (_int__,_ _optional_) – Maximum length of the returned list, defaults to -1 (no limit)
    
-   **offset** (_int__,_ _optional_) – Index to start searching from
    

Returns:

List of search results

Return type:

list

search\_companies(_keywords: List\[str\] | None \= None_, _\*\*kwargs_) → List

Perform a LinkedIn search for companies.

Parameters:

**keywords** (_list__,_ _optional_) – A list of search keywords (str)

Returns:

List of companies

Return type:

list

search\_jobs(_keywords: str | None \= None_, _companies: List\[str\] | None \= None_, _experience: List\[Literal\['1', '2', '3', '4', '5', '6'\]\] | None \= None_, _job\_type: List\[Literal\['F', 'C', 'P', 'T', 'I', 'V', 'O'\]\] | None \= None_, _job\_title: List\[str\] | None \= None_, _industries: List\[str\] | None \= None_, _location\_name: str | None \= None_, _remote: List\[Literal\['1', '2', '3'\]\] | None \= None_, _listed\_at\=86400_, _distance: int | None \= None_, _limit\=\-1_, _offset\=0_, _\*\*kwargs_) → List\[Dict\]

Perform a LinkedIn search for jobs.

Parameters:

-   **keywords** (_str__,_ _optional_) – Search keywords (str)
    
-   **companies** (_list__,_ _optional_) – A list of company URN IDs (str)
    
-   **experience** (_list__,_ _optional_) – A list of experience levels, one or many of “1”, “2”, “3”, “4”, “5” and “6” (internship, entry level, associate, mid-senior level, director and executive, respectively)
    
-   **job\_type** (_list__,_ _optional_) – A list of job types , one or many of “F”, “C”, “P”, “T”, “I”, “V”, “O” (full-time, contract, part-time, temporary, internship, volunteer and “other”, respectively)
    
-   **job\_title** (_list__,_ _optional_) – A list of title URN IDs (str)
    
-   **industries** (_list__,_ _optional_) – A list of industry URN IDs (str)
    
-   **location\_name** (_str__,_ _optional_) – Name of the location to search within. Example: “Kyiv City, Ukraine”
    
-   **remote** (_list__,_ _optional_) – Filter for remote jobs, onsite or hybrid. onsite:”1”, remote:”2”, hybrid:”3”
    
-   **listed\_at** (_int/str__,_ _optional. Default value is equal to 24 hours._) – maximum number of seconds passed since job posting. 86400 will filter job postings posted in last 24 hours.
    
-   **distance** (_int/str__,_ _optional. If not specified__,_ _None_ _or_ _0__,_ _the default value_ _of_ _25 miles applied._) – maximum distance from location in miles
    
-   **limit** (_int__,_ _optional__,_ _default -1_) – maximum number of results obtained from API queries. -1 means maximum which is defined by constants and is equal to 1000 now.
    
-   **offset** (_int__,_ _optional_) – indicates how many search results shall be skipped
    

Returns:

List of jobs

Return type:

list

search\_people(_keywords: str | None \= None_, _connection\_of: str | None \= None_, _network\_depths: List\[Literal\['F', 'S', 'O'\]\] | None \= None_, _current\_company: List\[str\] | None \= None_, _past\_companies: List\[str\] | None \= None_, _nonprofit\_interests: List\[str\] | None \= None_, _profile\_languages: List\[str\] | None \= None_, _regions: List\[str\] | None \= None_, _industries: List\[str\] | None \= None_, _schools: List\[str\] | None \= None_, _contact\_interests: List\[str\] | None \= None_, _service\_categories: List\[str\] | None \= None_, _include\_private\_profiles\=False_, _keyword\_first\_name: str | None \= None_, _keyword\_last\_name: str | None \= None_, _keyword\_title: str | None \= None_, _keyword\_company: str | None \= None_, _keyword\_school: str | None \= None_, _network\_depth: Literal\['F'\] | Literal\['S'\] | Literal\['O'\] | None \= None_, _title: str | None \= None_, _\*\*kwargs_) → List\[Dict\]

Perform a LinkedIn search for people.

Parameters:

-   **keywords** (_str__,_ _optional_) – Keywords to search on
    
-   **current\_company** (_list__,_ _optional_) – A list of company URN IDs (str)
    
-   **past\_companies** (_list__,_ _optional_) – A list of company URN IDs (str)
    
-   **regions** (_list__,_ _optional_) – A list of geo URN IDs (str)
    
-   **industries** (_list__,_ _optional_) – A list of industry URN IDs (str)
    
-   **schools** (_list__,_ _optional_) – A list of school URN IDs (str)
    
-   **profile\_languages** (_list__,_ _optional_) – A list of 2-letter language codes (str)
    
-   **contact\_interests** (_list__,_ _optional_) – A list containing one or both of “proBono” and “boardMember”
    
-   **service\_categories** (_list__,_ _optional_) – A list of service category URN IDs (str)
    
-   **network\_depth** (_str__,_ _optional_) – Deprecated, use network\_depths. One of “F”, “S” and “O” (first, second and third+ respectively)
    
-   **network\_depths** (_list__,_ _optional_) – A list containing one or many of “F”, “S” and “O” (first, second and third+ respectively)
    
-   **include\_private\_profiles** (_boolean__,_ _optional_) – Include private profiles in search results. If False, only public profiles are included. Defaults to False
    
-   **keyword\_first\_name** (_str__,_ _optional_) – First name
    
-   **keyword\_last\_name** (_str__,_ _optional_) – Last name
    
-   **keyword\_title** (_str__,_ _optional_) – Job title
    
-   **keyword\_company** (_str__,_ _optional_) – Company name
    
-   **keyword\_school** (_str__,_ _optional_) – School name
    
-   **connection\_of** (_str__,_ _optional_) – Connection of LinkedIn user, given by profile URN ID
    
-   **limit** (_int__,_ _optional_) – Maximum length of the returned list, defaults to -1 (no limit)
    

Returns:

List of profiles (minimal data only)

Return type:

list

send\_message(_message\_body: str_, _conversation\_urn\_id: str | None \= None_, _recipients: List\[str\] | None \= None_)

Send a message to a given conversation.

Parameters:

-   **message\_body** (_str_) – Message text to send
    
-   **conversation\_urn\_id** (_str__,_ _optional_) – LinkedIn URN ID for a conversation
    
-   **recipients** (_list__,_ _optional_) – List of profile urn id’s
    

Returns:

Error state. If True, an error occured.

Return type:

boolean

unfollow\_entity(_urn\_id: str_)

Unfollow a given entity.

Parameters:

**urn\_id** (_str_) – URN ID of entity to unfollow

Returns:

Error state. Returns True if error occurred

Return type:

boolean