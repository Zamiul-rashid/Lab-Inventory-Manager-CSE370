#!/usr/bin/env python3
"""
Populate the Lab Inventory Manager with Robotics Lab Equipment
Run this with: python manage.py populate_robotics_inventory
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from inventory.models import Product
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate the database with robotics lab inventory items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing products before adding new ones',
        )

    def handle(self, *args, **options):
        if options['clear']:
            Product.objects.all().delete()
            self.stdout.write(
                self.style.WARNING('Cleared all existing products')
            )

        # Get or create admin user to assign as creator
        admin_user = User.objects.filter(role='admin').first()
        if not admin_user:
            admin_user = User.objects.filter(is_staff=True).first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR('No admin user found. Please create an admin user first.')
            )
            return

        # Robotics Lab Inventory Data
        robotics_inventory = [
            # Arduino Boards
            {
                'name': 'Arduino Uno R3',
                'category': 'Microcontrollers',
                'description': 'ATmega328P-based microcontroller board with 14 digital pins, 6 analog pins, USB connection, and power jack. Perfect for beginners and prototyping.',
                'status': 'available'
            },
            {
                'name': 'Arduino Nano',
                'category': 'Microcontrollers',
                'description': 'Compact Arduino board with ATmega328P. Same functionality as Uno but in a breadboard-friendly form factor.',
                'status': 'available'
            },
            {
                'name': 'Arduino Mega 2560',
                'category': 'Microcontrollers',
                'description': 'ATmega2560-based board with 54 digital pins, 16 analog pins. Ideal for complex projects requiring more I/O pins.',
                'status': 'available'
            },
            {
                'name': 'Arduino Leonardo',
                'category': 'Microcontrollers',
                'description': 'ATmega32u4-based board with built-in USB communication. Can act as a keyboard or mouse.',
                'status': 'borrowed'
            },
            {
                'name': 'ESP32 Dev Board',
                'category': 'Microcontrollers',
                'description': 'Dual-core WiFi and Bluetooth enabled microcontroller. Perfect for IoT projects.',
                'status': 'available'
            },
            {
                'name': 'ESP8266 NodeMCU',
                'category': 'Microcontrollers',
                'description': 'WiFi-enabled microcontroller development board. Great for web server and IoT applications.',
                'status': 'available'
            },

            # Raspberry Pi Devices
            {
                'name': 'Raspberry Pi 4 Model B (8GB)',
                'category': 'Single Board Computers',
                'description': 'Latest Raspberry Pi with quad-core ARM processor, 8GB RAM, dual 4K display support, and Gigabit Ethernet.',
                'status': 'available'
            },
            {
                'name': 'Raspberry Pi 4 Model B (4GB)',
                'category': 'Single Board Computers',
                'description': 'Raspberry Pi 4 with 4GB RAM. Excellent for robotics, AI projects, and desktop replacement.',
                'status': 'borrowed'
            },
            {
                'name': 'Raspberry Pi Zero W',
                'category': 'Single Board Computers',
                'description': 'Ultra-compact Pi with WiFi and Bluetooth. Perfect for embedded projects and wearables.',
                'status': 'available'
            },
            {
                'name': 'Raspberry Pi Pico',
                'category': 'Microcontrollers',
                'description': 'RP2040-based microcontroller board. Low-cost, high-performance option for embedded applications.',
                'status': 'available'
            },

            # Raspberry Pi HATs
            {
                'name': 'Raspberry Pi Camera Module V2',
                'category': 'HATs & Modules',
                'description': '8MP camera module with 1080p video recording. CSI connector compatible.',
                'status': 'available'
            },
            {
                'name': 'Sense HAT',
                'category': 'HATs & Modules',
                'description': 'Multi-sensor board with LED matrix, accelerometer, gyroscope, magnetometer, temperature, pressure, and humidity sensors.',
                'status': 'available'
            },
            {
                'name': 'GPIO Expansion Board',
                'category': 'HATs & Modules',
                'description': 'Breadboard-friendly GPIO breakout board for Raspberry Pi. Includes LED indicators and resistors.',
                'status': 'available'
            },
            {
                'name': 'Motor Driver HAT',
                'category': 'HATs & Modules',
                'description': 'Dual motor driver HAT for controlling DC motors, stepper motors, and servos.',
                'status': 'borrowed'
            },

            # Sensors
            {
                'name': 'HC-SR04 Ultrasonic Sensor',
                'category': 'Sensors',
                'description': 'Non-contact distance sensor. Range: 2cm-4m. Perfect for obstacle avoidance robots.',
                'status': 'available'
            },
            {
                'name': 'DHT22 Temperature & Humidity Sensor',
                'category': 'Sensors',
                'description': 'Digital temperature and humidity sensor. High accuracy with calibrated output.',
                'status': 'available'
            },
            {
                'name': 'MPU6050 6-Axis Gyroscope & Accelerometer',
                'category': 'Sensors',
                'description': '6-axis motion tracking device. Combines 3-axis gyroscope and 3-axis accelerometer.',
                'status': 'available'
            },
            {
                'name': 'PIR Motion Sensor',
                'category': 'Sensors',
                'description': 'Passive Infrared sensor for motion detection. Ideal for security systems.',
                'status': 'available'
            },
            {
                'name': 'MQ-2 Gas Sensor',
                'category': 'Sensors',
                'description': 'Smoke and gas sensor. Detects LPG, propane, methane, alcohol, hydrogen.',
                'status': 'available'
            },
            {
                'name': 'BMP280 Barometric Pressure Sensor',
                'category': 'Sensors',
                'description': 'High precision atmospheric pressure sensor with temperature compensation.',
                'status': 'borrowed'
            },
            {
                'name': 'TCS3200 Color Recognition Sensor',
                'category': 'Sensors',
                'description': 'RGB color sensor with photodiodes and current-to-frequency converters.',
                'status': 'available'
            },
            {
                'name': 'Load Cell 5kg with HX711',
                'category': 'Sensors',
                'description': 'Weight sensor with 24-bit ADC. Perfect for digital scale projects.',
                'status': 'available'
            },

            # Actuators & Motors
            {
                'name': 'SG90 Micro Servo Motor',
                'category': 'Actuators',
                'description': '9g micro servo with 180° rotation. Torque: 2.5kg/cm. Operating voltage: 4.8-6V.',
                'status': 'available'
            },
            {
                'name': 'MG996R Servo Motor',
                'category': 'Actuators',
                'description': 'High torque metal gear servo. Torque: 9.4kg/cm. 180° rotation.',
                'status': 'available'
            },
            {
                'name': 'NEMA 17 Stepper Motor',
                'category': 'Actuators',
                'description': 'Bipolar stepper motor. 200 steps/revolution. High precision for 3D printers and CNC.',
                'status': 'borrowed'
            },
            {
                'name': 'DC Geared Motor 12V',
                'category': 'Actuators',
                'description': '12V DC motor with gear reduction. High torque, low speed. Perfect for robotics.',
                'status': 'available'
            },
            {
                'name': 'Brushless DC Motor',
                'category': 'Actuators',
                'description': 'High efficiency brushless motor with electronic speed controller (ESC).',
                'status': 'available'
            },

            # Motor Drivers
            {
                'name': 'L298N Motor Driver Module',
                'category': 'Motor Controllers',
                'description': 'Dual H-bridge motor driver. Can control 2 DC motors or 1 stepper motor. Max current: 2A per channel.',
                'status': 'available'
            },
            {
                'name': 'DRV8825 Stepper Motor Driver',
                'category': 'Motor Controllers',
                'description': 'Microstepping bipolar stepper motor driver. Up to 1/32 microstepping.',
                'status': 'available'
            },
            {
                'name': 'A4988 Stepper Driver',
                'category': 'Motor Controllers',
                'description': 'Stepper motor driver with translator and overcurrent protection. Up to 1/16 microstepping.',
                'status': 'borrowed'
            },

            # Display Modules
            {
                'name': '16x2 LCD Display with I2C',
                'category': 'Displays',
                'description': '16 character x 2 line LCD display with I2C backpack. Easy to connect with just 4 wires.',
                'status': 'available'
            },
            {
                'name': '0.96" OLED Display SSD1306',
                'category': 'Displays',
                'description': '128x64 pixel OLED display. I2C interface. White characters on black background.',
                'status': 'available'
            },
            {
                'name': '7-Segment 4-Digit Display',
                'category': 'Displays',
                'description': 'Common cathode 7-segment display with decimal points. Perfect for counters and clocks.',
                'status': 'available'
            },
            {
                'name': 'WS2812B LED Strip (1m)',
                'category': 'Displays',
                'description': 'Addressable RGB LED strip. 60 LEDs per meter. 5V power supply.',
                'status': 'available'
            },

            # Communication Modules
            {
                'name': 'HC-05 Bluetooth Module',
                'category': 'Communication',
                'description': 'Bluetooth serial communication module. Easy to pair and configure.',
                'status': 'available'
            },
            {
                'name': 'NRF24L01 2.4GHz Module',
                'category': 'Communication',
                'description': '2.4GHz wireless transceiver. Range up to 100m. Low power consumption.',
                'status': 'available'
            },
            {
                'name': 'SIM800L GSM Module',
                'category': 'Communication',
                'description': 'GSM/GPRS module for SMS and call functionality. Includes SMA antenna.',
                'status': 'borrowed'
            },
            {
                'name': 'ESP32-CAM Module',
                'category': 'Communication',
                'description': 'ESP32 with camera, WiFi, and Bluetooth. Perfect for surveillance and IoT camera projects.',
                'status': 'available'
            },

            # Power Supply & Components
            {
                'name': 'Breadboard 830 Points',
                'category': 'Prototyping',
                'description': 'Solderless breadboard with 830 tie points. Includes power rails.',
                'status': 'available'
            },
            {
                'name': 'Jumper Wire Set (M-M, M-F, F-F)',
                'category': 'Prototyping',
                'description': 'Set of 120 jumper wires in various lengths. Male-male, male-female, female-female.',
                'status': 'available'
            },
            {
                'name': '12V 5A Power Supply',
                'category': 'Power Supply',
                'description': 'Switching power adapter. Input: 100-240V AC. Output: 12V DC 5A.',
                'status': 'available'
            },
            {
                'name': 'Buck Converter LM2596',
                'category': 'Power Supply',
                'description': 'Step-down voltage regulator. Input: 4-40V. Output: 1.25-37V adjustable.',
                'status': 'available'
            },
            {
                'name': '18650 Battery Holder',
                'category': 'Power Supply',
                'description': 'Battery holder for 18650 lithium-ion cells. Includes charging protection circuit.',
                'status': 'available'
            },

            # Tools & Equipment
            {
                'name': 'Digital Multimeter',
                'category': 'Test Equipment',
                'description': 'Digital multimeter with voltage, current, resistance, and continuity testing.',
                'status': 'available'
            },
            {
                'name': 'Oscilloscope DSO138',
                'category': 'Test Equipment',
                'description': 'Digital oscilloscope DIY kit. 200kHz bandwidth. Ideal for learning.',
                'status': 'borrowed'
            },
            {
                'name': 'Function Generator',
                'category': 'Test Equipment',
                'description': 'Signal generator for sine, square, and triangle waves. Frequency range: 1Hz-1MHz.',
                'status': 'maintenance'
            },
            {
                'name': 'Soldering Iron Kit',
                'category': 'Tools',
                'description': 'Temperature-controlled soldering iron with tips, flux, and solder wire.',
                'status': 'available'
            },
            {
                'name': 'Wire Strippers & Crimping Tool',
                'category': 'Tools',
                'description': 'Multi-function tool for stripping wires and crimping connectors.',
                'status': 'available'
            },

            # Robot Chassis & Mechanical
            {
                'name': '4WD Robot Chassis Kit',
                'category': 'Mechanical',
                'description': 'Aluminum 4-wheel drive robot chassis with motors and wheels. Expandable design.',
                'status': 'available'
            },
            {
                'name': '2WD Smart Robot Car Kit',
                'category': 'Mechanical',
                'description': 'Beginner-friendly robot car chassis with ultrasonic sensor mount.',
                'status': 'borrowed'
            },
            {
                'name': 'Robot Arm Kit (6-DOF)',
                'category': 'Mechanical',
                'description': '6-degree-of-freedom robot arm with servo motors. Includes gripper.',
                'status': 'available'
            },
            {
                'name': 'Acrylic Robot Platform',
                'category': 'Mechanical',
                'description': 'Clear acrylic platform for custom robot builds. Multiple mounting holes.',
                'status': 'available'
            },
        ]

        created_count = 0
        for item_data in robotics_inventory:
            # Add some variety by randomly assigning some items as borrowed/maintenance
            if random.random() < 0.1:  # 10% chance
                item_data['status'] = random.choice(['borrowed', 'maintenance'])
            
            product, created = Product.objects.get_or_create(
                name=item_data['name'],
                defaults={
                    'category': item_data['category'],
                    'description': item_data['description'],
                    'status': item_data['status'],
                    'created_by': admin_user,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'✓ Created: {product.name}')
            else:
                self.stdout.write(f'• Exists: {product.name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully populated database with {created_count} new robotics lab items!'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Total items in database: {Product.objects.count()}'
            )
        )
