#include <WiFi.h>
#include <HTTPClient.h>

// Exemple simple: remplacez ces valeurs par votre hotspot mobile.
const char* ssid = "AERF-HOME";
const char* password = "fatick2026";

// En local, utilisez l'adresse IP du PC sur le meme reseau WiFi.
// Exemple: http://192.168.1.149:8000/api/positions/
const char* serverUrl = "http://192.168.1.149:8000/api/positions/";
const char* apiKey = "mototrack-baol-express-2026";

int motoId = 1;

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);

  Serial.print("Connexion WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("Connecte. IP ESP32: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // Dans votre projet, remplacez ces valeurs par celles lues depuis le GPS NEO-6M.
  float latitude = 14.7886;
  float longitude = -16.9260;
  float vitesse = 35.5;

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-KEY", apiKey);

    String payload = "{";
    payload += "\"moto_id\":" + String(motoId) + ",";
    payload += "\"latitude\":" + String(latitude, 6) + ",";
    payload += "\"longitude\":" + String(longitude, 6) + ",";
    payload += "\"vitesse\":" + String(vitesse, 1);
    payload += "}";

    int httpCode = http.POST(payload);
    Serial.print("Code HTTP: ");
    Serial.println(httpCode);
    Serial.println(http.getString());
    http.end();
  } else {
    Serial.println("WiFi deconnecte");
  }

  delay(10000);
}
