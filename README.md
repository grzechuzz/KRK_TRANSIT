### [🇬🇧 English Version](README_EN.md)

# KRKtransit - mapa na żywo oraz statystyki opóźnień pojazdów komunikacji miejskiej w Krakowie

Platforma dostarczająca statystyki opóźnień pojazdów komunikacji miejskiej (MPK, Mobilis) w Krakowie w czasie rzeczywistym. Bazuje ona na danych dostarczanych przez ZTP w Krakowie, udostępnionych zgodnie ze specyfikacją GTFS (Static & Realtime). 

Umożliwia m.in. identyfikację odcinków na których powstają największe opóźnienia, monitorowanie długofalowych trendów opóźnień dla każdej linii oraz śledzenie pojazdów na żywo.  

Aby uniknąć fałszowania wyników przez nierealistyczne opóźnienia, statystyki nie uwzględniają pierwszego i ostatniego przystanku kursu. 

**Strona:** https://krktransit.pl/

**GTFS**: https://gtfs.org/documentation/overview/

**Dane ZTP**: https://gtfs.ztp.krakow.pl/

<img width="1912" height="944" alt="image" src="https://github.com/user-attachments/assets/12410f06-6d1e-472e-b6c8-5492d4441027" />

<img width="1912" height="468" alt="image" src="https://github.com/user-attachments/assets/1bb9e101-0788-4f35-a6e4-70e3a4112ff0" />

<img width="1912" height="733" alt="image" src="https://github.com/user-attachments/assets/b422d0ba-30c9-4ed1-9ae9-a8e6d5e20e5e" />

## Architektura

System składa się z pięciu serwisów, z których każdy realizuje konkretny etap przepływu danych. Moduły serwisów nie
importują się bezpośrednio nawzajem i są rozdzielone względem odpowiedzialności. Backend, a dokładniej główna ścieżka pobierania, przetwarzania i zapisu danych ma charakter `event-driven data pipeline`.

Projekt celowo opiera się na współdzielonej bazie danych, bo przy tej skali mikroserwisy raczej tylko
utrudniłyby życie. Baza danych podzielona jest na trzy osobne schematy: `gtfs_static`, `events` oraz `weather`.

<p align="center">
<img width="569" height="927" alt="image" src="https://github.com/user-attachments/assets/bbd842d9-e373-4322-8252-03a249e0a245" />
</p>

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

## Użyte technologie
- Python 3.13
- FastAPI + Uvicorn
- PostgreSQL 17 (główna baza danych)
- Redis 7 (cache + Pub/Sub)
- msgspec (serializacja), protobuf + gtfs-realtime-bindings (parsowanie GTFS)
- SQLAlchemy 2.0 
- Alembic
- GitHub Actions (CI)
- Docker

