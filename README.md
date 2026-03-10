### [🇬🇧 English Version](README_EN.md)

# KRKtransit - statystyki opóźnień autobusów komunikacji miejskiej w Krakowie

REST API dostarczające statystyki opóźnień autobusów (MPK, Mobilis) w Krakowie w czasie rzeczywistym. Bazuje ono na danych dostarczanych przez ZTP w Krakowie, udostępnionych zgodnie ze specyfikacją GTFS (Static & Realtime). 

API umożliwia m.in. identyfikację odcinków na których powstają największe opóźnienia oraz monitorowanie długofalowych trendów opóźnień dla każdej linii.  

Dostępne są również endpointy z pozycjami pojazdów na żywo oraz geometrią tras.

**API:** https://api.krktransit.pl/docs

**GTFS**: https://gtfs.org/documentation/overview/

**Dane ZTP**: https://gtfs.ztp.krakow.pl/


## Endpointy API

Aby uniknąć fałszowania wyników przez nierealistyczne opóźnienia, statystyki nie uwzględniają pierwszego i ostatniego przystanku kursu.

| Endpoint | Opis |
|---|---|
| `GET /v1/lines/{line}/stats/max-delay` | Top 10 przyrostów opóźnień między kolejnymi przystankami |
| `GET /v1/lines/{line}/stats/route-delay` | Top 10 opóźnień wygenerowanych na całej trasie |
| `GET /v1/lines/{line}/stats/punctuality` | Statystyki punktualności według progów opoźnień |
| `GET /v1/lines/{line}/stats/trend` | Dzienny trend średniego opóźnienia |
| `GET /v1/vehicles/positions` | Pozycje GPS wszystkich aktywnych pojazdów na żywo |
| `GET /v1/shapes/{shape_id}` | Geometria trasy (uporządkowane punkty GPS) |

Dokumentacja: [api.krktransit.pl/docs](https://api.krktransit.pl/docs)

## Architektura

System składa się z czterech serwisów.

| Serwis | Rola |
|---|---|
| **Importer** | Pobiera i ładuje dane GTFS Static (trasy, przystanki, rozkłady, kształty tras) dla obu przewoźników. Wykrywa zmiany w plikach poprzez hashowanie SHA-256. Uruchamia migracje przy starcie. |
| **RT Poller** | Pobiera feedy `VehiclePositions.pb` i `TripUpdates.pb` co 5 sekund. Publikuje przetworzone pozycje pojazdów na Redis Pub/Sub i cache'uje predykcje z trip updates. |
| **Stop Writer** | Nasłuchuje pozycji pojazdów z Redis Pub/Sub. Wykrywa zdarzenia na przystankach czterema metodami (patrz niżej). Zapisuje zdarzenia do bazy danych. |
| **API** | Udostępnia statystyki opóźnień, dane punktualności, trendy dzienne, pozycje pojazdów na żywo i geometrię tras. Cache'uje odpowiedzi dotyczące statysyk w Redisie. |

## Detekcja zdarzeń na przystankach

Główna logika (w stop_writer/detector.py) analizuje dane z VehiclePositions.pb oraz TripUpdates.pb i określa kiedy pojazd odwiedził przystanek.

| Metoda | Trigger | Źródło czasu |
|---|---|---|
| `STOPPED_AT` | Pojazd wysyła status `STOPPED_AT` | Timestamp GPS |
| `SEQ_JUMP` | Skok w sekwencji przystanków (pominięte przystanki) | Cache predykcji z TripUpdates |
| `TIMEOUT` | Pojazd rozpoczął nowy kurs (zamykanie poprzedniego) | Cache predykcji z TripUpdates dla poprzedniego kursu |

Zdarzenia estymowane są walidowane względem następnego potwierdzonego `STOPPED_AT`. Zdarzenia z niemożliwymi timestampami lub nierealistycznymi spadkami opóźnień są odrzucane.

Endpointy udostepniające maksymalne opóźnienie pomiędzy dwoma przystankami oraz statystyki punktualności według określonych progów wykluczają zdarzenia z metodą `SEQ_JUMP`, ponieważ estymowane czasy mogą zawyżać wyniki na poziomie pojedynczych przystanków. 

## Użyte technologie
- Python 3.13
- FastAPI + Uvicorn
- PostgreSQL 17 (główna baza danych)
- Redis 7 (cache)
- msgspec (serializacja), protobuf + gtfs-realtime-bindings (parsowanie GTFS)
- SQLAlchemy 2.0 
- Alembic
- Caddy (serwer WWW i reverse proxy z automatyczną obsługą HTTPS) 
- GitHub Actions (CI)
- Docker

## Uruchomienie lokalne

1. Sklonuj repozytorium:
```bash
git clone https://github.com/grzechuzz/KRK_TRANSIT_STATS.git
```

2. Stwórz potrzebne pliki:
   - `secrets/db_password` — hasło PostgreSQL
   - `secrets/redis_password` — hasło Redis
   - `redis/users.acl` — plik ACL Redis
   - `docker/.env` — zmienne `POSTGRES_DB`, `POSTGRES_USER`, `REDIS_USER`

3. Uruchom kontenery:
```bash
cd docker
docker compose up -d --build
```

4. Otwórz dokumentację API:
```
http://localhost/docs
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


