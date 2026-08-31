Field	Type	Example

transaction\_id	string	txn\_00042

subscription\_id	string	sub\_1183

customer\_id	string	cust\_0512

amount	number	999

currency	string	INR

payment\_method	enum	card / upi / netbanking / wallet / upi\_autopay

decline\_code	enum	see list below

gateway\_message	string	free text, e.g. "Your card has insufficient funds"

attempt\_number	int	1

timestamp	ISO datetime	2026-08-15T09:32:00Z

customer\_tenure\_months	int	14

prior\_successful\_payments	int	13

prior\_failed\_payments	int	1

customer\_email	string	user0512@example.com

customer\_phone	string	+91XXXXXXXXXX (fake)





Field	Type	Example

transaction\_id	string	txn\_00042

recoverable	bool	true

recovers\_with\_action	enum or null	retry / switch\_method / nudge / escalate / null if unrecoverable

base\_success\_probability	float 0-1	0.6 (used by your Day 1 simulator)

