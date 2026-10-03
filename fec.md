https://api.open.fec.gov/developers/

An official website of the United States GovernmentUS flag signifying that this is a United States Federal Government websiteFederal Election Commission | United States of America
OpenFEC
 1.0 
/swagger/
This application programming interface (API) allows you to explore the way candidates and committees fund their campaigns.

The Federal Election Commission (FEC) API is a RESTful web service supporting full-text and field-specific searches on FEC data. Bulk downloads are available on the current site. Information is tied to the underlying forms by file ID and image ID. Data are updated nightly.

There are a lot of data, and a good place to start is to use search to find interesting candidates and committees. Then, you can use their IDs to find report or line item details with the other endpoints. If you are interested in individual donors, check out contributor information in the /schedule_a/ endpoints.

Getting started with the openFEC API

If you would like to use the FEC's API programmatically, you can sign up for your own API key using our form. Alternatively, you can still try out our API without an API key by using the web interface and using DEMO_KEY. Note that when you use the openFEC API you are subject to the Terms of Service and Acceptable Use policy.

Signing up for an API key will enable you to place up to 1,000 calls an hour. Each call is limited to 100 results per page. You can email questions, comments or a request to get a key for 7,200 calls an hour (120 calls per minute) to APIinfo@fec.gov. You can also ask questions and discuss the data in a community led group.

The model definitions and schema are available at /swagger. This is useful for making wrappers and exploring the data.

A few restrictions limit the way you can use FEC data. For example, you can’t use contributor lists for commercial purposes or to solicit donations. Learn more here.

Inspect our source code. We welcome issues and pull requests!



Sign up for an API key
Your API key for jonathanherr@gmail.com has been e-mailed to you. You can use your API key to begin making web service requests immediately.

If you don't receive your API Key via e-mail within a few minutes, please contact us.

For additional support, please contact us. When contacting us, please tell us what API you're accessing and provide the following account details so we can quickly find you:

Account Email: jonathanherr@gmail.com
Account ID: b84d0e1f-34a5-41bb-ba5f-4054020e64ad
candidate
Candidate endpoints give you access to information about the people running for office. This information is organized by candidate_id. If you're unfamiliar with candidate IDs, using /candidates/search/ will help you locate a particular candidate.Officially, a candidate is an individual seeking nomination for election to a federal office. People become candidates when they (or agents working on their behalf) raise contributions or make expenditures that exceed $5,000.The candidate endpoints primarily use data from FEC registration Form 1 for committee information and Form 2 for candidate information.
committee
Committees are entities that spend and raise money in an election. Their characteristics and relationships with candidates can change over time.You might want to use filters or search endpoints to find the committee you're looking for. Then you can use other committee endpoints to explore information about the committee that interests you.Financial information is organized by committee_id, so finding the committee you're interested in will lead you to more granular financial information.The committee endpoints include all FEC filers, even if they aren't registered as a committee.Officially, committees include the committees and organizations that file with the FEC. Several different types of organizations file financial reports with the FEC:Campaign committees authorized by particular candidates to raise and spend funds in their campaigns. Non-party committees (e.g., PACs), some of which may be sponsored by corporations, unions, trade or membership groups, etc. Political party committees at the national, state, and local levels. Groups and individuals making only independent expenditures Corporations, unions, and other organizations making internal communicationsThe committee endpoints primarily use data from FEC registration Form 1 and Form 2.
dates
Reporting deadlines, election dates FEC meetings, events etc.
financial
Fetch key information about a committee's Form 3, Form 3X, Form 13, or Form 3P financial reports.Most committees are required to summarize their financial activity in each filing; those summaries are included in these files. Generally, committees file reports on a quarterly or monthly basis, but some must also submit a report 12 days before primary elections. Therefore, during the primary season, the period covered by this file may be different for different committees. These totals also incorporate any changes made by committees, if any report covering the period is amended.Information is made available on the API as soon as it's processed. Keep in mind, complex paper filings take longer to process.The financial endpoints use data from FEC form 5, for independent expenditors; or the summary and detailed summary pages of the FEC Form 3, for House and Senate committees; Form 3X, for PACs and parties; Form 13 for inaugural committees; and Form 3P, for presidential committees.
search
Search for candidates, committees by name.
filings
All official records and reports filed by or delivered to the FEC.Note: because the filings data includes many records, counts for large result sets are approximate; you will want to page through the records until no records are returned.
receipts
This collection of endpoints includes Schedule A records reported by a committee. Schedule A records describe itemized receipts, including contributions from individuals. If you are interested in contributions from individuals, use the /schedules/schedule_a/ endpoint. For a more complete description of all Schedule A records visit About receipts data. If you are interested in our "is_individual" methodology visit our methodology page.Schedule A is also available as a database dump file that is updated weekly on Sunday. The database dump files are here: https://www.fec.gov/files/bulk-downloads/index.html?prefix=bulk-downloads/data-dump/schedules/. The instructions are here: https://www.fec.gov/files//bulk-downloads/data-dump/schedules/README.txt. We cannot provide help with restoring the database dump files, but you can refer to this community led group for discussion.
disbursements
Schedule B filings describe itemized disbursements. This data explains how committees and other filers spend their money. These figures are reported as part of forms F3, F3X and F3P.
loans
Schedule C shows all loans, endorsements and loan guarantees a committee receives or makes.
debts
Schedule D, it shows debts and obligations owed to or by the committee that are required to be disclosed.
independent expenditures
Schedule E covers the line item expenditures for independent expenditures. For example, if a super PAC bought ads on TV to oppose a federal candidate, each ad purchase would be recorded here with the expenditure amount, name and id of the candidate, and whether the ad supported or opposed the candidate.An independent expenditure is an expenditure for a communication "expressly advocating the election or defeat of a clearly identified candidate that is not made in cooperation, consultation, or concert with, or at the request or suggestion of, a candidate, a candidate’s authorized committee, or their agents, or a political party or its agents."Aggregates by candidate do not include 24 and 48 hour reports. This ensures we don't double count expenditures and the totals are more accurate. You can still find the information from 24 and 48 hour reports in /schedule/schedule_e/.
party-coordinated expenditures
Schedule F, it shows all special expenditures a national or state party committee makes in connection with the general election campaigns of federal candidates.
communication cost
Reports of communication costs by corporations and membership organizations from the FEC F7 forms.
electioneering
An electioneering communication is any broadcast, cable or satellite communication that fulfills each of the following conditions:The communication refers to a clearly identified federal candidate.The communication is publicly distributed by a television station, radio station, cable television system or satellite system for a fee.The communication is distributed within 60 days prior to a general election or 30 days prior to a primary election to federal office.
presidential
Data supporting fec.gov's presidential map.For more information about the presidential map data available to download from fec.gov, please visit: https://www.fec.gov/campaign-finance-data/presidential-map-data/
filer resources
Useful tools for those who file with the FEC.Look up RAD analyst with telephone extension by committee_id.
national party accounts
Collection of endpoints that provide information about national party committee accounts including presidential nominating conventions, national party headquarters buildings, and election recounts and contests and other legal proceedings accounts.
efiling
Efiling endpoints provide real-time campaign finance data received from electronic filers. Efiling endpoints only contain the most recent four months of data and don't contain the processed and coded data that you can find on other endpoints.
audit
The agency’s monitoring process may detect potential violations through a review of a committee’s reports or through a Commission audit. By law, all enforcement cases must remain confidential until they’re closed.The Commission is required by law to audit Presidential campaigns that accept public funds. In addition, the Commission audits a committee when it appears not to have met the threshold requirements for substantial compliance with the Federal Election Campaign Act. The audit determines whether the committee complied with limitations, prohibitions and disclosure requirements.These endpoints contain Final Audit Reports approved by the Commission since inception.
legal
Explore relevant statutes, regulations and Commission actions.

Models
Seal of the Federal Election Commission | United States of America
Federal Election Commission

The FEC's Twitter page
The FEC's YouTube page
