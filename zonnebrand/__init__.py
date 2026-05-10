from zonnebrand.zonnebrand import Zonnebrand

__author__ = 'Erdogan Tasksen'
__email__ = 'erdogant@gmail.com'
__version__ = '0.2.0'


# module level doc-string
__doc__ = """
zonnebrand
========================================================================================

This library is for automatic regulation of the solar panels based on EPEX prices.
It identifies negative-price windows, and automatically controls the solar panel activation to 0% (during negative prices) or 100% (otherwise).

Rules
-----
- Only act when a contiguous negative-price window is >= MIN_WINDOW_MINUTES.
- Two parameters are updated every time a change is needed:
    Parameter.PCC.FlbInv.WMaxNom  (Fallback begr. werk. verm. in %)
    Parameter.PCC.WMaxNom         (Ingest. limiet werkel. vermogen op netaansl. %)
- The loop re-evaluates once per minute but only logs in to Sunny Portal
  when the desired state actually changes.

Usage
-------
>>> python zonnebrand.py --help                                             # show all options
>>> python zonnebrand.py                                                    # normal price-based control loop
>>> python zonnebrand.py --headless                                         # show the browser when setting paramaters active
>>> python zonnebrand.py --provider zonneplan                               # normal price-based control loop
>>> python zonnebrand.py --provider zonneplan --mail your_mail@gmail.com    # normal price-based control loop
>>> python zonnebrand.py --set 0                                            # immediately force export limit to 0%
>>> python zonnebrand.py --set 100                                          # immediately force export limit to 100%

References
----------
https://github.com/erdogant/zonnebrand

"""
