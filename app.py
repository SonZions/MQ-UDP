import paho.mqtt.client as mqtt
import socket
import threading

# MQTT-Konfigurationsparameter
MQTT_BROKER = "loxberry"
MQTT_PORT = 1883
MQTT_TOPIC = "test/topic"

# UDP-Konfigurationsparameter
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

# Variable zur Verfolgung der gesendeten Nachrichten
sent_messages = set()

# Funktion zum Senden von Nachrichten an das UDP-Ziel
def send_udp_message(message):
    # Nachricht nur senden, wenn sie noch nicht gesendet wurde
    if message not in sent_messages:
        sent_messages.add(message)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message.encode(), (UDP_IP, UDP_PORT))
        print(f"UDP Nachricht gesendet: {message}")

# Callback, wenn eine MQTT-Nachricht empfangen wird
def on_message(client, userdata, msg):
    message = msg.payload.decode()
    print(f"MQTT Nachricht empfangen: {message}")
    send_udp_message(message)

# MQTT-Verbindung und Abonnieren des Themas
def mqtt_to_udp():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_forever()

# UDP-Empfang und Nachricht an MQTT senden
def udp_to_mqtt(client):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    while True:
        data, addr = sock.recvfrom(1024)
        message = data.decode()
        print(f"UDP Nachricht empfangen: {message}")
        client.publish(MQTT_TOPIC, message)

# Hauptfunktion
def main():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    # Thread für MQTT -> UDP
    mqtt_thread = threading.Thread(target=mqtt_to_udp)
    mqtt_thread.start()

    # Thread für UDP -> MQTT
    udp_thread = threading.Thread(target=udp_to_mqtt, args=(client,))
    udp_thread.start()

    mqtt_thread.join()
    udp_thread.join()

if __name__ == "__main__":
    main()
