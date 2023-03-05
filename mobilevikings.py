import requests, re, json, urllib, locale, math
from datetime import datetime, tzinfo, timezone

def sizeof_fmt(num, suffix="b"):
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"
def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

def aslocaltimestr(utc_dt):
    return utc_to_local(utc_dt).strftime('%Y-%m-%d %H:%M')

username = "xxxxxxxxx@xxxxxxxxxx.com"
password = "xxxxxxxxxxxxxxxxxxx"

headers = {
    "accept-language": "nl-BE,nl;q=0.9",
    "sec-ch-ua": "\" Not A;Brand\";v=\"99\", \"Chromium\";v=\"100\", \"Google Chrome\";v=\"100\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "Windows",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
}

extraHeaders = {
    "authority": "mobilevikings.be",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
}

response = requests.get("https://mobilevikings.be/nl/my-viking/login", headers={**headers,**extraHeaders})
if response.status_code == 200:
    z = re.findall(r"{\"baseUrl\".*}",response.text)
    if z:
        j = json.loads(z[0])
        extraHeaders = {
            "authority": "uwa.mobilevikings.be",
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded"
        }
        data = {
            "username": username,
            "password": password,
            "grant_type": "password",
            "client_id": j["uwa"]["oauthClientId"],
            "client_secret": j["uwa"]["oauthClientSecret"],
        }

        response = requests.post('https://uwa.mobilevikings.be/mv/oauth2/token/', headers={**headers,**extraHeaders}, data=urllib.parse.urlencode(data))
        if response.status_code == 200:
            j = response.json()
            extraHeaders = {
                "authority": "uwa.mobilevikings.be",
                "accept": "application/json",
                "authorization": "Bearer "+j["access_token"]
            }

            response = requests.get("https://uwa.mobilevikings.be/20220211/mv/subscriptions", headers={**headers,**extraHeaders})
            output = "{"
            if response.status_code == 200:
                j = response.json()
                now = datetime.now(timezone.utc)
                for s in j:
                    output += '"'+s["sim"]["alias"]+'": {'
                    output += '"nummer": "'+s["sim"]["msisdn"]+'",'
                    response = requests.get("https://uwa.mobilevikings.be/20200901/mv/subscriptions/"+s["id"]+"/balance", headers={**headers,**extraHeaders})
                    b = response.json()
                    if response.status_code == 200:
                        output += '"product": "'+b["product"]["descriptions"]["description"]+'",'
                        for x in b["bundles"]:
                            if x["category"] == 'default':
                                if x["type"] == 'data':
                                    output += '"'+x["type"]+'_verbruikt": "'+sizeof_fmt(x["used"])+'",'
                                elif x["type"] == 'voice':
                                    output += '"'+x["type"]+'_verbruikt": "'+str(round(x["used"]/60))+" min"+'",'
                                else:
                                    output += '"'+x["type"]+'_verbruikt": "'+str(round(x["used"]))+'",'
                                if x["total"] == -1:
                                    output += '"'+x["type"]+'_totaal": "∞",'
                                else:
                                    if x["type"] == 'data':
                                        output += '"'+x["type"]+'_totaal": "'+sizeof_fmt(x["total"])+'",'
                                        output += '"'+x["type"]+'_verbruik": "'+sizeof_fmt(x["used"])+"/"+sizeof_fmt(x["total"])+'",'
                                        output += '"'+x["type"]+'_resterend": "'+sizeof_fmt(x["total"]-x["used"])+'",'
                                    elif x["type"] == 'voice':
                                        output += '"'+x["type"]+'_totaal": "'+str(round(x["total"]/60))+' min",'
                                        output += '"'+x["type"]+'_verbruik": "'+str(round(x["used"]/60))+"/"+str(round(x["total"]/60))+" min"+'",'
                                        output += '"'+x["type"]+'_resterend": "'+str(round((x["total"]/60)-(x["used"]/60)))+'",'
                                    if x["type"] == 'data' or x["type"] == 'voice':
                                        output += '"'+x["type"]+'_percentage": "'+str(math.floor(100*x["used"]/x["total"]))+'",'
                                output += '"'+x["type"]+'_periode": "'+aslocaltimestr(datetime.strptime(x["valid_from"], '%Y-%m-%dT%H:%M:%S%z'))+" - "+aslocaltimestr(datetime.strptime(x["valid_until"], '%Y-%m-%dT%H:%M:%S%z'))+'",'
                                output += '"'+x["type"]+'_from": "'+aslocaltimestr(datetime.strptime(x["valid_from"], '%Y-%m-%dT%H:%M:%S%z'))+'",'
                                output += '"'+x["type"]+'_until": "'+aslocaltimestr(datetime.strptime(x["valid_until"], '%Y-%m-%dT%H:%M:%S%z'))+'",'
                                output += '"'+x["type"]+'_dagen_resterend": "'+str((datetime.strptime(x["valid_until"], '%Y-%m-%dT%H:%M:%S%z') - now).days)+'",'
                                periode = (datetime.strptime(x["valid_until"], '%Y-%m-%dT%H:%M:%S%z') - datetime.strptime(x["valid_from"], '%Y-%m-%dT%H:%M:%S%z')).days
                                in_periode = periode - (datetime.strptime(x["valid_until"], '%Y-%m-%dT%H:%M:%S%z') - now).days
                                period_used_percentage = 100*in_periode/periode
                                output += '"'+x["type"]+'_dagen_periode": "'+str((datetime.strptime(x["valid_until"], '%Y-%m-%dT%H:%M:%S%z') - datetime.strptime(x["valid_from"], '%Y-%m-%dT%H:%M:%S%z')).days)+'",'
                                output += '"'+x["type"]+'_period_used_percentage": "'+str(round(period_used_percentage))+'",'
                    output = output[:-1]
                    output += "},"
            if output[-1] == ',':
                output = output[:-1]
            output += "}"
print(output)

