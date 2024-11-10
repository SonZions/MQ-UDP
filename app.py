# ja ja
import paho.mqtt.client as mqtt
import socket
import threading

# Konfigurationen
MQTT_BROKER = 'mqtt.example.com'
MQTT_PORT = 1883
MQTT_TOPIC = 'test/topic'
UDP_IP = '127.0.0.1'
UDP_PORT = 5005

# UDP Socket erstellen
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Callback, wenn eine MQTT-Nachricht empfangen wird
def on_mqtt_message(client, userdata, msg):
    print(f"MQTT empfangen: {msg.topic} {msg.payload}")
    # MQTT Nachricht an UDP senden
    udp_sock.sendto(msg.payload, (UDP_IP, UDP_PORT))

# MQTT-Client initialisieren und verbinden
def init_mqtt_client():
    client = mqtt.Client()
    client.on_message = on_mqtt_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(MQTT_TOPIC)
    return client

# Funktion zum Empfangen von UDP-Nachrichten und Senden an MQTT
def udp_to_mqtt(client):
    udp_sock.bind((UDP_IP, UDP_PORT))
    while True:
        data, addr = udp_sock.recvfrom(1024)
        print(f"UDP empfangen: {data} von {addr}")
        client.publish(MQTT_TOPIC, data)

# Main-Funktion
def main():
    # MQTT-Client starten
    mqtt_client = init_mqtt_client()

    # Thread für UDP zu MQTT starten
    udp_thread = threading.Thread(target=udp_to_mqtt, args=(mqtt_client,))
    udp_thread.start()

    # MQTT-Client-Schleife starten
    mqtt_client.loop_forever()

if __name__ == "__main__":
    main()
