#!/bin/bash

# Simplified OpenSearch GCP Setup (without VPC Connector)
# Development environment with internal access

set -e

# Configuration
PROJECT_ID="ragp-472304"
REGION="asia-northeast3"
ZONE="asia-northeast3-a"
OPENSEARCH_INSTANCE_NAME="opensearch-dev"
MACHINE_TYPE="e2-medium"  # Development size
DISK_SIZE="20GB"

echo "🚀 Setting up simplified OpenSearch infrastructure..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Machine Type: $MACHINE_TYPE (Development)"

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "📋 Enabling required APIs..."
gcloud services enable compute.googleapis.com

# Create firewall rule for OpenSearch (allow external access for development)
echo "🔒 Creating firewall rules..."
gcloud compute firewall-rules create allow-opensearch-dev \
    --allow=tcp:9200,tcp:9300 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=opensearch-server \
    --description="Allow OpenSearch access for development" || echo "Firewall rule already exists"

# Create firewall rule for SSH
gcloud compute firewall-rules create allow-ssh-opensearch \
    --allow=tcp:22 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=opensearch-server \
    --description="Allow SSH to OpenSearch server" || echo "SSH firewall rule already exists"

# Create startup script for OpenSearch installation
cat > opensearch-startup.sh << 'EOF'
#!/bin/bash

# Update system
apt-get update
apt-get install -y curl wget gnupg2 software-properties-common apt-transport-https ca-certificates

# Install OpenJDK 11
apt-get install -y openjdk-11-jdk

# Set JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> /etc/environment
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# Create opensearch user
useradd -m -d /home/opensearch -s /bin/bash opensearch

# Download and install OpenSearch
cd /opt
wget https://artifacts.opensearch.org/releases/bundle/opensearch/2.11.1/opensearch-2.11.1-linux-x64.tar.gz
tar -xzf opensearch-2.11.1-linux-x64.tar.gz
mv opensearch-2.11.1 opensearch
chown -R opensearch:opensearch /opt/opensearch

# Configure OpenSearch for development (no security, external access)
cat > /opt/opensearch/config/opensearch.yml << 'OSEOF'
cluster.name: rag-opensearch-dev
node.name: opensearch-node-1
path.data: /opt/opensearch/data
path.logs: /opt/opensearch/logs
network.host: 0.0.0.0
http.port: 9200
discovery.type: single-node
plugins.security.disabled: true
bootstrap.memory_lock: false
http.cors.enabled: true
http.cors.allow-origin: "*"
http.cors.allow-methods: OPTIONS, HEAD, GET, POST, PUT, DELETE
http.cors.allow-headers: "X-Requested-With, Content-Type, Content-Length, Authorization"
OSEOF

# Configure JVM heap size for development (1GB)
cat > /opt/opensearch/config/jvm.options << 'JVMEOF'
-Xms1g
-Xmx1g
-XX:+UseG1GC
-XX:G1HeapRegionSize=16m
-XX:+UseLargePages
-XX:+UnlockExperimentalVMOptions
-XX:+UseTransparentHugePages
-Djava.io.tmpdir=/var/lib/opensearch/tmp
JVMEOF

# Create directories
mkdir -p /opt/opensearch/data /opt/opensearch/logs /var/lib/opensearch/tmp
chown -R opensearch:opensearch /opt/opensearch
chown -R opensearch:opensearch /var/lib/opensearch

# Set up systemd service
cat > /etc/systemd/system/opensearch.service << 'SERVICEEOF'
[Unit]
Description=OpenSearch
Documentation=https://opensearch.org/
Wants=network-online.target
After=network-online.target
StartLimitIntervalSec=0

[Service]
Type=notify
RuntimeDirectory=opensearch
RuntimeDirectoryMode=755
Environment=OPENSEARCH_HOME=/opt/opensearch
Environment=OPENSEARCH_PATH_CONF=/opt/opensearch/config
Environment=PID_DIR=/var/run/opensearch
Environment=ES_HOME=/opt/opensearch
Environment=ES_PATH_CONF=/opt/opensearch/config
EnvironmentFile=-/etc/default/opensearch

WorkingDirectory=/opt/opensearch
User=opensearch
Group=opensearch

ExecStart=/opt/opensearch/bin/opensearch

StandardOutput=journal
StandardError=inherit

LimitNOFILE=65535
LimitNPROC=4096
LimitAS=infinity
LimitFSIZE=infinity
TimeoutStopSec=0
KillSignal=SIGTERM
KillMode=process
SendSIGKILL=no
SuccessExitStatus=143

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Enable and start OpenSearch
systemctl daemon-reload
systemctl enable opensearch
systemctl start opensearch

# Wait for OpenSearch to start
echo "Waiting for OpenSearch to start..."
sleep 30

# Verify OpenSearch is running
curl -X GET "localhost:9200/_cluster/health?pretty"

echo "OpenSearch installation completed!"
EOF

# Make startup script executable
chmod +x opensearch-startup.sh

# Create the Compute Engine instance
echo "💻 Creating Compute Engine instance: $OPENSEARCH_INSTANCE_NAME"
gcloud compute instances create $OPENSEARCH_INSTANCE_NAME \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --network-interface=subnet=default,address="" \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --service-account=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")-compute@developer.gserviceaccount.com \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --tags=opensearch-server \
    --create-disk=auto-delete=yes,boot=yes,device-name=$OPENSEARCH_INSTANCE_NAME,image=projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts,mode=rw,size=$DISK_SIZE,type=projects/$PROJECT_ID/zones/$ZONE/diskTypes/pd-standard \
    --metadata-from-file startup-script=opensearch-startup.sh \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --reservation-affinity=any

echo "⏳ Waiting for OpenSearch installation to complete..."
sleep 120

# Get external IP of OpenSearch instance
OPENSEARCH_EXTERNAL_IP=$(gcloud compute instances describe $OPENSEARCH_INSTANCE_NAME \
    --zone=$ZONE \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "✅ OpenSearch instance created successfully!"
echo "External IP: $OPENSEARCH_EXTERNAL_IP"
echo "OpenSearch URL: http://$OPENSEARCH_EXTERNAL_IP:9200"

echo "🧪 Testing OpenSearch connectivity..."
sleep 30
curl -f "http://$OPENSEARCH_EXTERNAL_IP:9200/_cluster/health?pretty" || echo "OpenSearch not ready yet, may need more time"

echo "🎉 Setup completed!"
echo ""
echo "📋 Summary:"
echo "- OpenSearch Instance: $OPENSEARCH_INSTANCE_NAME"
echo "- External IP: $OPENSEARCH_EXTERNAL_IP"
echo "- Machine Type: $MACHINE_TYPE (Development)"
echo "- OpenSearch URL: http://$OPENSEARCH_EXTERNAL_IP:9200"
echo ""
echo "🔗 Next steps:"
echo "1. Update Cloud Run backend environment variables:"
echo "   OPENSEARCH_HOST=$OPENSEARCH_EXTERNAL_IP"
echo "   OPENSEARCH_PORT=9200"
echo ""
echo "⚠️  Note: This is a development setup with security disabled and external access enabled."

# Clean up startup script
rm opensearch-startup.sh

echo "Setup completed successfully!"