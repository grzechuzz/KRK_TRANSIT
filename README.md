### [🇬🇧 English Version](README_EN.md)

# KRKtransit - mapa na żywo oraz statystyki opóźnień pojazdów komunikacji miejskiej w Krakowie

Platforma dostarczająca statystyki opóźnień pojazdów komunikacji miejskiej (MPK, Mobilis) w Krakowie w czasie rzeczywistym. Bazuje ona na danych dostarczanych przez ZTP w Krakowie, udostępnionych zgodnie ze specyfikacją GTFS (Static & Realtime). 

Umożliwia m.in. identyfikację odcinków na których powstają największe opóźnienia, monitorowanie długofalowych trendów opóźnień dla każdej linii oraz śledzenie pojazdów na żywo.  

Kod można uruchomić lokalnie, co pozwala na samodzielne archiwizowanie danych o zrealizowanych kursach i budowanie własnej, historycznej bazy opóźnień.

**Strona:** https://krktransit.pl/

**API:** https://api.krktransit.pl/docs

**GTFS**: https://gtfs.org/documentation/overview/

**Dane ZTP**: https://gtfs.ztp.krakow.pl/

<img width="1912" height="944" alt="image" src="https://github.com/user-attachments/assets/12410f06-6d1e-472e-b6c8-5492d4441027" />

<img width="1912" height="468" alt="image" src="https://github.com/user-attachments/assets/1bb9e101-0788-4f35-a6e4-70e3a4112ff0" />

<img width="1912" height="733" alt="image" src="https://github.com/user-attachments/assets/b422d0ba-30c9-4ed1-9ae9-a8e6d5e20e5e" />



## Endpointy API

Aby uniknąć fałszowania wyników przez nierealistyczne opóźnienia, statystyki nie uwzględniają pierwszego i ostatniego przystanku kursu.

| Endpoint | Opis |
|---|---|
| `GET /v1/lines/{line}/stats/max-delay` | Top 10 przyrostów opóźnień między kolejnymi przystankami |
| `GET /v1/lines/{line}/stats/route-delay` | Top 10 opóźnień wygenerowanych na całej trasie |
| `GET /v1/lines/{line}/stats/punctuality` | Statystyki punktualności według progów opóźnień |
| `GET /v1/lines/{line}/stats/trend` | Dzienny trend średniego opóźnienia |
| `GET /v1/vehicles/positions` | Pozycje GPS wszystkich aktywnych pojazdów na żywo |
| `GET /v1/shapes/{shape_id}` | Geometria trasy (uporządkowane punkty GPS) |
| `GET /v1/trips/{trip_id}/stops` | Przystanki na danej trasie |
| `GET /health` | Health check |

Dokumentacja: [api.krktransit.pl/docs](https://api.krktransit.pl/docs)

## Architektura

System składa się z pięciu serwisów.

| Serwis | Rola |
|---|---|
| **Importer** | Pobiera i ładuje dane GTFS Static (trasy, przystanki, rozkłady, kształty tras) dla obu przewoźników. Wykrywa zmiany w plikach poprzez hashowanie SHA-256. |
| **RT Poller** | Pobiera dane z `VehiclePositions.pb` i `TripUpdates.pb`. Publikuje przetworzone pozycje pojazdów na Redis Pub/Sub i cache'uje predykcje z trip updates. |
| **Stop Writer** | Nasłuchuje pozycji pojazdów z Redis Pub/Sub. Wykrywa zdarzenia na przystankach trzema metodami (patrz niżej). Zapisuje zdarzenia do bazy danych. |
| **API** | Udostępnia statystyki opóźnień, dane punktualności, trendy dzienne, pozycje pojazdów na żywo i geometrię tras. Cache'uje odpowiedzi dotyczące statystyk w Redisie. |
| **Weather Collector** | Pobiera historyczne dane pogodowe z Open-Meteo i zapisuje do bazy danych. |

## Detekcja zdarzeń na przystankach

| Metoda | Trigger | Źródło czasu |
|---|---|---|
| `STOPPED_AT` | Pojazd wysyła status `STOPPED_AT` | Timestamp GPS |
| `SEQ_JUMP` | Skok w sekwencji przystanków (pominięte przystanki) | Cache predykcji z TripUpdates |
| `TIMEOUT` | Pojazd rozpoczął nowy kurs (zamykanie poprzedniego) | Cache predykcji z TripUpdates dla poprzedniego kursu |

Zdarzenia estymowane (`SEQ_JUMP`, `TIMEOUT`) są dostępne opcjonalnie przez parametr `?include_estimated=true`. Domyślnie API zwraca wyłącznie zdarzenia wykryte poprzez `STOPPED_AT`.

## Użyte technologie
- Python 3.13
- FastAPI + Uvicorn
- PostgreSQL 17 (główna baza danych)
- Redis 7 (cache)
- msgspec (serializacja), protobuf + gtfs-realtime-bindings (parsowanie GTFS)
- SQLAlchemy 2.0 
- Alembic
- GitHub Actions (CI)
- Docker

## Uruchomienie lokalne

1. Sklonuj repozytorium:
```bash
git clone https://github.com/grzechuzz/KRK_TRANSIT.git
```

2. Stwórz potrzebne pliki:
   
   - `secrets/db_password` (admin bazy)
   - `secrets/db_password_api` (tylko odczyt dla API)
   - `secrets/db_password_writer` (zapis danych RT)
   - `secrets/db_password_importer` (zapis danych GTFS)
   - `secrets/db_password_weather_collector` (zapis danych pogodowych)
   - `secrets/redis_password`
   - `redis/users.acl`
   
  Przykładowy `redis/users.acl`
  
   ```
   user mpk_redis on >CHANGE_THAT_PASSWORD ~* &* +@read +@write +@string +@hash +@set +@list +@pubsub +@keyspace +@connection -@dangerous
   user default off
   ```

   Utwórz plik `docker/.env` i uzupełnij zmienne:
   ```env
   POSTGRES_DB=
   POSTGRES_USER=
   IMPORTER_USER=
   WRITER_USER=
   API_READER_USER=
   WEATHER_COLLECTOR_USER=
   REDIS_USER=
   ```
   
3. Uruchom kontenery:
```bash
cd docker
docker compose up -d --build
```

4. Otwórz dokumentację API:
```
http://localhost:8000/docs
```

## Testy i linter

```bash
pip install -e ".[dev]"

pytest                  # testy jednostkowe
ruff check .            # linting
ruff format --check .   # formatowanie
mypy .                  # sprawdzanie typów
```

CI uruchamia wszystko przy każdym pushu do maina.
