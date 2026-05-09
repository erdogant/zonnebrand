[![Python](https://img.shields.io/pypi/pyversions/zonnebrand)](https://img.shields.io/pypi/pyversions/zonnebrand)
[![Pypi](https://img.shields.io/pypi/v/zonnebrand)](https://pypi.org/project/zonnebrand/)
[![Docs](https://img.shields.io/badge/Sphinx-Docs-Green)](https://erdogant.github.io/zonnebrand/)
[![LOC](https://sloc.xyz/github/erdogant/zonnebrand/?category=code)](https://github.com/erdogant/zonnebrand/)
[![Downloads](https://static.pepy.tech/personalized-badge/zonnebrand?period=month&units=international_system&left_color=grey&right_color=brightgreen&left_text=PyPI%20downloads/month)](https://pepy.tech/project/zonnebrand)
[![Downloads](https://static.pepy.tech/personalized-badge/zonnebrand?period=total&units=international_system&left_color=grey&right_color=brightgreen&left_text=Downloads)](https://pepy.tech/project/zonnebrand)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/erdogant/zonnebrand/blob/master/LICENSE)
[![Forks](https://img.shields.io/github/forks/erdogant/zonnebrand.svg)](https://github.com/erdogant/zonnebrand/network)
[![Issues](https://img.shields.io/github/issues/erdogant/zonnebrand.svg)](https://github.com/erdogant/zonnebrand/issues)
[![Project Status](http://www.repostatus.org/badges/latest/active.svg)](http://www.repostatus.org/#active)
[![Donate](https://img.shields.io/badge/Support%20this%20project-grey.svg?logo=github%20sponsors)](https://erdogant.github.io/zonnebrand/pages/html/Documentation.html#)

<div>
<a href="https://erdogant.github.io/zonnebrand/">
  <img src="https://raw.githubusercontent.com/erdogant/zonnebrand/master/docs/figs/logo.png" alt="Zonnebrand Logo" width="250" align="left" />
</a>
It detects negative-price windows and adjusts the two export-limit parameters in ennexOS: 0% during negative prices and 100% otherwise.
⭐️ Star this project if you like it ⭐️
</div>


---


# Rules

- When EPEX spot prices are detected changed from positive to negative or the otherway arround, then set SMA parameters are updated:

  - `Parameter.PCC.FlbInv.WMaxNom` → fallback active power limit (%)
  - `Parameter.PCC.WMaxNom` → grid export limit (%)

- The system checks prices every 15 minutes.
- Login to Sunny Portal only happens when a **state change is required**.

---

# Usage

```bash
python zonnebrand.py --help                # show all options
python zonnebrand.py                       # run normal price-based control loop
python zonnebrand.py --mail                # send status updates using resend
python zonnebrand.py --browser             # run with browser visible for debugging
python zonnebrand.py --provider zonneplan  # use Zonneplan as price source
python zonnebrand.py --plot                # plot price chart
python zonnebrand.py --data                # fetch and print price data
python zonnebrand.py --set 0               # force export limit to 0%
python zonnebrand.py --set 100             # force export limit to 100%
```

# Multiple parameters can be given

```bash
python zonnebrand.py --provider zonneplan --plot --mail mypersonalmail@gmail.com
```

<hr>


# Docker usage

## Build & run (recommended first time)
```bash
docker compose up -d --build
docker compose build
```

## Start existing container
```bash
docker compose up -d
```

## List images
```bash
docker ps
docker image ls
```

## Cleanup unused resources
```bash
docker system prune
docker builder prune
docker rm -f <container_id>
```


---


### Contributors
<p align="left">
  <a href="https://github.com/erdogant/zonnebrand/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=erdogant/zonnebrand" />
  </a>
</p>

### Maintainer
* Erdogan Taskesen, github: [erdogant](https://github.com/erdogant)
* Contributions are welcome.

[![Buy me a coffee](https://img.buymeacoffee.com/button-api/?text=Buy+me+a+coffee&emoji=&slug=erdogant&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff)](https://www.buymeacoffee.com/erdogant)
