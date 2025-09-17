#!/bin/bash

# OpenSearch GCP Infrastructure Setup Script
# Development environment with VPC-internal communication only

set -e

# Configuration
PROJECT_ID="ragp-472304"
REGION="asia-northeast3"
ZONE="asia-northeast3-a"
VPC_NAME="rag-vpc"
SUBNET_NAME="rag-subnet"
OPENSEARCH_INSTANCE_NAME="opensearch-dev"
MACHINE_TYPE="e2-medium"  # Development size
DISK_SIZE="20GB"          # Small disk for development

echo "🚀 Setting up OpenSearch infrastructure in GCP..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Machine Type: $MACHINE_TYPE (Development)"

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "📋 Enabling required APIs..."
gcloud services enable compute.googleapis.com
gcloud services enable vpc-access.googleapis.com

# Create VPC network
echo "🌐 Creating VPC network: $VPC_NAME"
gcloud compute networks create $VPC_NAME \
    --subnet-mode=custom \
    --description="VPC for RAG system with OpenSearch"

# Create subnet
echo "🔗 Creating subnet: $SUBNET_NAME"
gcloud compute networks subnets create $SUBNET_NAME \
    --network=$VPC_NAME \
    --range=10.0.0.0/24 \
    --region=$REGION \
    --description="Subnet for OpenSearch and Cloud Run"

# Create firewall rule for OpenSearch (internal VPC only)
echo "🔒 Creating firewall rules for VPC-internal access..."
gcloud compute firewall-rules create allow-opensearch-internal \
    --network=$VPC_NAME \
    --allow=tcp:9200,tcp:9300 \
    --source-ranges=10.0.0.0/24 \
    --description="Allow OpenSearch access within VPC"

# Create firewall rule for SSH (for maintenance)
gcloud compute firewall-rules create allow-ssh-opensearch \
    --network=$VPC_NAME \
    --allow=tcp:22 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=opensearch-server \
    --description="Allow SSH to OpenSearch server"

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

# Download and install OpenSearch
cd /opt
wget https://artifacts.opensearch.org/releases/bundle/opensearch/2.11.1/opensearch-2.11.1-linux-x64.tar.gz
tar -xzf opensearch-2.11.1-linux-x64.tar.gz
mv opensearch-2.11.1 opensearch
chown -R opensearch:opensearch /opt/opensearch

# Create opensearch user
useradd -m -d /home/opensearch -s /bin/bash opensearch

# Configure OpenSearch
cat > /opt/opensearch/config/opensearch.yml << 'OSEOF'
cluster.name: rag-opensearch-dev
node.name: opensearch-node-1
path.data: /opt/opensearch/data
path.logs: /opt/opensearch/logs
network.host: 0.0.0.0
http.port: 9200
discovery.type: single-node
plugins.security.disabled: true
bootstrap.memory_lock: true
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

# Set proper ownership
chown -R opensearch:opensearch /opt/opensearch

# Create data and logs directories
mkdir -p /opt/opensearch/data /opt/opensearch/logs
chown -R opensearch:opensearch /opt/opensearch/data /opt/opensearch/logs

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
    --network-interface=subnet=$SUBNET_NAME,no-address \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --service-account=$(gcloud config get-value account) \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --tags=opensearch-server \
    --create-disk=auto-delete=yes,boot=yes,device-name=$OPENSEARCH_INSTANCE_NAME,image=projects/ubuntu-os-cloud/global/images/family/ubuntu-2004-lts,mode=rw,size=$DISK_SIZE,type=projects/$PROJECT_ID/zones/$ZONE/diskTypes/pd-standard \
    --metadata-from-file startup-script=opensearch-startup.sh \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --reservation-affinity=any

echo "⏳ Waiting for OpenSearch installation to complete..."
sleep 60

# Get internal IP of OpenSearch instance
OPENSEARCH_INTERNAL_IP=$(gcloud compute instances describe $OPENSEARCH_INSTANCE_NAME \
    --zone=$ZONE \
    --format='get(networkInterfaces[0].networkIP)')

echo "✅ OpenSearch instance created successfully!"
echo "Internal IP: $OPENSEARCH_INTERNAL_IP"
echo "OpenSearch URL: http://$OPENSEARCH_INTERNAL_IP:9200"

# Create VPC Access Connector for Cloud Run
echo "🔌 Creating VPC Access Connector for Cloud Run..."
gcloud compute networks vpc-access connectors create rag-connector \
    --network=$VPC_NAME \
    --region=$REGION \
    --range=10.1.0.0/28 \
    --machine-type=e2-micro \
    --min-instances=2 \
    --max-instances=3

echo "🎉 Infrastructure setup completed!"
echo ""
echo "📋 Summary:"
echo "- VPC Network: $VPC_NAME"
echo "- Subnet: $SUBNET_NAME (10.0.0.0/24)"
echo "- OpenSearch Instance: $OPENSEARCH_INSTANCE_NAME"
echo "- Internal IP: $OPENSEARCH_INTERNAL_IP"
echo "- Machine Type: $MACHINE_TYPE (Development)"
echo "- VPC Connector: rag-connector"
echo ""
echo "🔗 Next steps:"
echo "1. Update Cloud Run backend environment variables:"
echo "   OPENSEARCH_HOST=$OPENSEARCH_INTERNAL_IP"
echo "   OPENSEARCH_PORT=9200"
echo "2. Deploy backend with VPC connector: --vpc-connector rag-connector"
echo ""
echo "🧪 Test OpenSearch connectivity:"
echo "   gcloud compute ssh $OPENSEARCH_INSTANCE_NAME --zone=$ZONE"
echo "   curl http://localhost:9200/_cluster/health"

# Clean up startup script
rm opensearch-startup.sh

echo "Setup script completed successfully!"