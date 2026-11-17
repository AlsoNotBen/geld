# Changelog

### v0.1.1

#
### v0.1.0

#### New
* Claims 
  * These now generate the accounting entries on the backend. A claim is in DRAFT until approved, once approved it generates the relevant journal entries.
  * Expense/Creditor Claims - Allows a user to set a multi-line claim with the option to upload supporting documents per line
  * Insurance Claim - Allows a user to submit a multi-line claim for insurance payouts.
  * Displays Claims awaiting approval, Paid and Unpaid claims and the claims cost breakdown in the Dashboard.

#### Improvements
* Adding changelog (should've done this long ago lol)

#### Bug Fixes 
* Added guards preventing page crash when user doesn't have company membership

#### Notes
* When creating a new company from the /admin panel, it will not run `accounting.setup.seed_model()`, however we don't want to import this function as it creates a circular dependency between the `accounting` and `shared` modules. This is an architectural red line which I will not cross. Will need to come up with another plan or workflow to solve the issue (creating a 
new company via admin panel doesn't populate any Accounts fields).
#