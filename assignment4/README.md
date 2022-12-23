## Overview

For the [fourt assignment](/assignment4/HY436_assignment_4.pdf) I ran an instance of [Artemis](https://github.com/FORTH-ICS-INSPIRE/artemis) using a custom [configutation file](/assignment4/config.yaml) (code can be found below) to suit the assignment’s needs. In the config file there is a prefix watched (snd_assignment4) which is requested from the assignment. The source AS (sdn_assignment4_asn) and the neighbor AS (sdn_assignment4_neighbor) are also set up and a rule connecting ASes and prefixes is present too. Also a monitor is setup according to the basic config file from the git repository

Configuration File:
```yaml
#
# ARTEMIS Configuration File (HY436 Assignment4)
#
# Start of Prefix Definitions
prefixes:
  sdn_assignment4: &sdn_assignment4
  - 184.164.247.0/24
# End of Prefix Definitions

# Start of ASN Definitions
asns:
  sdn_assignment4_asn: &sdn_assignment4_asn
  - 61574
  sdn_assignment4_neighbor: &sdn_assignment4_neighbor
  - 47065
# End of ASN Definitions

# Start of Monitor Definitions
monitors:
  riperis: ['']
  bgpstreamlive:
  - routeviews
  - ris
  bgpstreamkafka:
    host: bmp.bgpstream.caida.org
    port: 9092
    topic: '^openbmp\.router--.+\.peer-as--.+\.bmp_raw'
  bgpstreamhist: '/etc/artemis/'
# End of Monitor Definitions

# Start of Rule Definitions
rules:
- prefixes:
  - *sdn_assignment4
  origin_asns:
  - *sdn_assignment4_asn
  neighbors:
  - *sdn_assignment4_neighbor
  mitigation: manual
# End of Rule Definitions 
```

## Results

In the screenshots included below are the [hijacks](https://bgpartemis.readthedocs.io/en/latest/hijackinfo/) found by Artemis. In total two types of hijacks were picked up by my implementation, E|0|-|- and E|1|-|-. E|0|-|- means that there was a hijack for the exact prefix (sdn_assignment4) with an illegal origin. E|1|-|- means that there was a hijack for the exact prefix (sdn_assignment4) with a legal origin but an illegal first hop. In the second screenshot an ongoing hijack can also be noticed!

- E|0|-|- hijacks: ![E|0|-|- hijacks](/assignment4/screenshots/E0_hijacks.png)

- E|1|-|- hijacks: ![E|1|-|- hijacks](/assignment4/screenshots/E1_hijacks.png)

