## Get a profile and their connections, then send a message

~~~
<span></span><span>import</span> <span>json</span>

<span>from</span> <span>linkedin_api</span> <span>import</span> <span>Linkedin</span>

<span>with</span> <span>open</span><span>(</span><span>"credentials.json"</span><span>,</span> <span>"r"</span><span>)</span> <span>as</span> <span>f</span><span>:</span>
    <span>credentials</span> <span>=</span> <span>json</span><span>.</span><span>load</span><span>(</span><span>f</span><span>)</span>

<span>if</span> <span>credentials</span><span>:</span>
    <span>linkedin</span> <span>=</span> <span>Linkedin</span><span>(</span><span>credentials</span><span>[</span><span>"username"</span><span>],</span> <span>credentials</span><span>[</span><span>"password"</span><span>])</span>

    <span>profile</span> <span>=</span> <span>linkedin</span><span>.</span><span>get_profile</span><span>(</span><span>"ACoAABQ11fIBQLGQbB1V1XPBZJsRwfK5r1U2Rzw"</span><span>)</span>
    <span>profile</span><span>[</span><span>"contact_info"</span><span>]</span> <span>=</span> <span>linkedin</span><span>.</span><span>get_profile_contact_info</span><span>(</span>
        <span>"ACoAABQ11fIBQLGQbB1V1XPBZJsRwfK5r1U2Rzw"</span>
    <span>)</span>
    <span>connections</span> <span>=</span> <span>linkedin</span><span>.</span><span>get_profile_connections</span><span>(</span><span>profile</span><span>[</span><span>"profile_id"</span><span>])</span>
    <span># send a message</span>
    <span>linkedin</span><span>.</span><span>send_message</span><span>(</span>
        <span>recipients</span><span>=</span><span>[</span><span>profile</span><span>[</span><span>"profile_id"</span><span>]],</span>
        <span>message</span><span>=</span><span>"Hello, Hola, Namaste, Hii, Bonjour, Guten Tag"</span><span>,</span>
    <span>)</span>
~~~