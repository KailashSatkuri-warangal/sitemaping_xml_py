import requests
import json

username = "satkuri_Kailash"
url = "https://leetcode.com/graphql/"

query = """
query getUserProfile($username: String!) {
  matchedUser(username: $username) {
    username
    profile {
      realName
      aboutMe
      countryName
      skillTags
      reputation
      ranking
    }
    submitStats {
      acSubmissionNum {
        difficulty
        count
      }
    }
  }
}
"""

payload = {"query": query, "variables": {"username": username}}
headers = {"Content-Type": "application/json"}

r = requests.post(url, json=payload, headers=headers)
data = r.json()

user = data.get("data", {}).get("matchedUser")
if user:
	print("Username:", user.get("username"))
	prof = user.get("profile", {})
	print("Skills:", prof.get("skillTags"))
	print("Reputation:", prof.get("reputation"))
	stats = user.get("submitStats", {}).get("acSubmissionNum", [])
	print("Solved problems:")
	for item in stats:
		print(" ", item.get("difficulty"), ":", item.get("count"))
else:
	print("No user data returned")
