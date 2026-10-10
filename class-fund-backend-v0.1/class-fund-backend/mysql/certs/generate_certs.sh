#!/bin/bash
# Generate self-signed SSL certificates for MySQL

# Create CA
openssl genrsa 2048 > ca-key.pem
openssl req -new -x509 -nodes -days 3650 -key ca-key.pem -out ca.pem -subj "/CN=CLASS_FUND_CA"

# Create server certificate
openssl req -newkey rsa:2048 -nodes -days 3650 -keyout server-key.pem -out server-req.pem -subj "/CN=mysql-primary"
openssl rsa -in server-key.pem -out server-key.pem
openssl x509 -req -in server-req.pem -days 3650 -CA ca.pem -CAkey ca-key.pem -set_serial 01 -out server-cert.pem

# Create client certificate
openssl req -newkey rsa:2048 -nodes -days 3650 -keyout client-key.pem -out client-req.pem -subj "/CN=classfund-client"
openssl rsa -in client-key.pem -out client-key.pem
openssl x509 -req -in client-req.pem -days 3650 -CA ca.pem -CAkey ca-key.pem -set_serial 02 -out client-cert.pem

# Verify certificates
openssl verify -CAfile ca.pem server-cert.pem client-cert.pem

# Set permissions
chmod 600 *-key.pem
chmod 644 *-cert.pem ca.pem

echo "Certificates generated successfully"