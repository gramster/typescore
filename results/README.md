Some modules fail and don't appear in score list. An incomplete list:

- protobuf - gets installed under 'google' but there is no top_level.txt file in dist-info
- pyrsistent/pvectorc - is native code
- kiwisolver/src - doesn't exist
- dnspython - installs into dns but has no top_level.txt file pointing us there
- poetry-core - installs into poetry but has no top_level.txt file pointing us there
- ujson - is native code
- xgboost/libxgboost is native code




