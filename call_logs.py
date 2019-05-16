#!/usr/bin/env python3

import postgresql
import re
import requests
import yaml
import calendar
import sys
from collections import defaultdict

if len(sys.argv) != 2:
  print("Synopsis:", sys.argv[0], "<path-to-config.yml>")
  sys.exit(1)

config        = yaml.load(open(sys.argv[1], 'r'))
connection    = postgresql.open(**config['postgres'])
influx        = config['influx']
measurement   = influx['measurement']
url           = "%swrite?db=%s&precision=s" % (influx['url'], influx['database'])
zones         = []
current_time  = None
current_calls = None
influxdata    = []


for items in config['zones']:
  for zone, pattern in items.items():
    zones.append((zone, re.compile(pattern)))


def getZone(number):
  for zone, pattern in zones:
    if pattern.match(number):
      return zone
  raise "unknown zone for number {}" % number


class Sampler:
    def __init__(self):
        self.count    = 0
        self.duration = 0
    def add(self, duration):
        self.count    += 1
        self.duration += duration


def escapeTag(key,value):
  if value==None:
    return ""
  value = re.sub('[^A-Za-z0-9 ]+', '', value.strip())
  return "," + key + "=" + re.sub(' ', '\\ ', value)

def clearTimeframe():
  global current_calls

  if current_calls:
    for (direction,gateway,zone), sampler in current_calls.items():
      influxdata.append("%s,direction=%s%s%s calls=%di,seconds=%di %d" % (
        measurement,
        direction,
        escapeTag('gateway',gateway),
        escapeTag('zone',zone),
        sampler.count,
        sampler.duration,
        current_time,
      ))

  current_calls = defaultdict(Sampler)


dn_gateways = {}

rows = connection.query.rows("\
  SELECT value, gateway.name AS gateway_name \
  FROM dn \
  INNER JOIN externalline ON externalline.fkiddn = dn.iddn \
  INNER JOIN gateway      ON gateway.idgateway = externalline.idexternalline")

for row in rows:
  dn_gateways[row['value']] = row['gateway_name']

# seg_type=2 answered call log segment
rows = connection.query.rows("SELECT * FROM cl_segments_view WHERE seg_type=2 ORDER BY dst_start_time")

for row in rows:
  zone    = None
  gateway = None

  if row['src_dn_type'] == 1:
    # call from extern
    direction = 'incoming'
    gateway   = dn_gateways[row['src_dn']]
  elif row['dst_dn_type'] == 1:
    # call to extern
    direction = 'outgoing'
    zone      = getZone(row['dst_caller_number'])
    gateway   = dn_gateways[row['dst_dn']]
  else:
    # internal
    direction = 'internal'

  # start time at the beginning of the hour
  ts       = calendar.timegm(row['dst_start_time'].replace(second=0, microsecond=0, minute=0).timetuple())
  duration = row['dst_end_time']-row['dst_answer_time']

  if current_time != ts:
    clearTimeframe()
    current_time  = ts

  current_calls[(direction,gateway,zone)].add(duration.seconds)

clearTimeframe()


# Submit to InfluxDB
response = requests.post(url,
  data="\n".join(influxdata),
  auth=(influx['username'], influx['password'])
)

# Check result
if response.status_code != 204:
  print(response.text)
  response.raise_for_status()

