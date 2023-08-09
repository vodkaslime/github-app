# app-count-files

## Setup
To install smee nodejs dependencies:
```
yarn install
```

To install python app dependencies:
```
pip install -r requirements.txt
```

## Run locally in dev env:
Run smee as webhook routing:
```
yarn smee -u https://smee.io/zBGEd0gAm117mmdG -t http://localhost:3000
```

Then run python app in local dev:
```
DEV_ENV=true uvicorn src.main:app --host 0.0.0.0 --port 3000 --reload
```

## Run in prod deployment env:
```
uvicorn src.main:app --host 0.0.0.0 --port 3000
```