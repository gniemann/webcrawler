<p>We have created a graphical web crawler that allows users to create an interactive map to explore the interconnections (hyperlinks) among web pages. Users interact with this service by entering a URL from which to start exploring and other parameters in a form. Users can explore via either a breadth first or depth first search from their URL of interest. Upon submitting the form information, the web crawler generates a map, and it is dynamically constructed within a grid map area for the user to view. The grid itself allows users to zoom in and out, drag the grid around, and drag individual map nodes. When a user highlights one of the map nodes the URL the node represents appears. Users can click on these nodes to open these URLS in a separate window.

<p>The features of the Graphical Web Crawler are:
<ol>
<li>Front-end client-side user interface that provides the user the ability to specify a starting URL and specify a depth-first or breadth-first crawl, as well as a numeric limit to terminate the crawl.</li>
<li>Back-end server-side crawler that performs the requested crawl.</li>
<li>Back-end transmits results to the front-end, which displays them graphically for the user to inspect.</li>
<li>The URLs of the crawled pages/nodes will be displayed, and the user may click them to navigate to them in a new tab or window.</li>
<li>The option to provide a keyword that the back-end crawler will use as a sentinel to end the crawl, i.e. prior to reaching the numeric limit.</li>
<li>The client-side user interface should use cookies to store the previous starting pages, if the user wishes to re-crawl them.</li>
<li>UI will build and display the graph in real-time.</li>
<li>Graph will use a physics simulation to organize itself interactively, in real-time.</li>
<li>Nodes will display the site favicon, if available.</li>
</ol>

<p>The working system is hosted on Google App Engine and available at <a href="https://gammacrawler.appspot.com">https://gammacrawler.appspot.com</a>

<p>

