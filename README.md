This progam utilizes InDesign's DataMerge feature to autofill a template with article headlines, article bodies, author names, article images, and auto-generated qr-code article links from any WordPress.com site with an enabled REST API.
This allows for the rapid publication of readily-updated newsletter publications, while eliminating the errors that come from manually moving data from a WordPress site into an InDesign template.


If you want to test this program, you can find a live demo hosted [here](https://fp-flyer-generator.streamlit.app/).


I originally created this program while I was editor of the student newspaper at Front Range Community College [FRCC], to increase the speed and accuracy at which we could produce our "stand flyers", promotional documents with article previews, along with QR codes which linked to our site. In September, I ported this program to Python so I could host it as a web app.

Note that many sites hosted with WordPress have their REST APIs disabled, and sites hosted with WordPress.org use an entirely different API that this tool isn't compatible with. This is unfortunate, since most major sites (the source of the "40% of the internet is WordPress!" claims) are self-hosted with WordPress.org. That said, Some sites you can test this tool with include:

[Flickr's Blog](https://blog.flickr.net/en)

[Mozilla's blog](https://blog.mozilla.org)

[The Front Page!](https://thefrontpagefrcc.com)
