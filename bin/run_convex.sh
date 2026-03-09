#!/usr/bin/env bash

set -eu
trap 'kill 0' EXIT
export RUST_BACKTRACE=1 
export RUST_LOG=info,common::errors=debug
print_banner() {
    local instance_name="$1"
    local port="$2"
    local proxy_port="$3"
    local data_dir="$4"

    echo "=================================================="
    echo "  CONVEX LOCAL INSTANCE: ${instance_name}         "
    echo "=================================================="
    echo "  Backend (Origin) : http://localhost:${port}     "
    echo "  Site Proxy       : http://localhost:${proxy_port}"
    echo "  Data Directory   : ${data_dir}                   "
    echo "=================================================="
    echo ""
}

run_convex_backend() {
    local instance_name="$1"
    local secret="$2"
    local port="$3"
    local proxy_port="$4"
    local data_base_dir="$5"
    
    # Generate a valid 32-byte hex key from the provided secret (using sha256)
    # This ensures "password" becomes a valid hex string that the backend accepts
    local hex_secret=$(python -c "import hashlib, sys; print(hashlib.sha256(sys.argv[1].encode('utf-8')).hexdigest())" "${secret}")

    local instance_dir="${data_base_dir}/${instance_name}"
    local db_path="${instance_dir}/db.sqlite3"
    local storage_dir="${instance_dir}/storage"

    echo "INFO: Initializing Convex backend configuration"
    echo "INFO: Instance Name: ${instance_name}"
    echo "INFO: Port: ${port}"
    echo "INFO: Site Proxy Port: ${proxy_port}"
    echo "INFO: Instance Directory: ${instance_dir}"
    echo "INFO: Secret (Derived): ${hex_secret}"

    mkdir -p "${instance_dir}"
    mkdir -p "${storage_dir}"

    local backend_bin="$(dirname "$0")/convex-local-backend"
    

    if [ ! -f "$backend_bin" ]; then
        # Fallback to checking PATH
        if command -v convex-local-backend &> /dev/null; then
            backend_bin="convex-local-backend"
        else
            echo "ERROR: convex-local-backend binary not found in ${binaries_dir} or PATH"
            exit 1
        fi
    fi
    
    echo "INFO: Using binary at ${backend_bin}"

    echo "=================================================="
    echo "  GENERATING ADMIN KEY...                         "
    echo "=================================================="
    local admin_key
    admin_key=$(python $(dirname "$0")/generate_admin_key.py "${instance_name}" "${hex_secret}")
    
    if [ -z "$admin_key" ]; then
        echo "ERROR: Failed to generate admin key."
        exit 1
    fi
    
    echo "  Instance Name    : ${instance_name}"
    echo "  Admin Key        : ${admin_key}"
    echo "=================================================="
    echo ""
    echo "Starting Convex Backend..."

    "${backend_bin}" \
        --instance-name "${instance_name}" \
        --instance-secret "${hex_secret}" \
        --port "${port}" \
        --site-proxy-port "${proxy_port}" \
        --convex-origin "http://localhost:${port}" \
        --convex-site "http://localhost:${proxy_port}" \
        --local-storage "${storage_dir}" \
        --disable-beacon \
        "${db_path}" &
    
    local backend_pid=$!

    echo "INFO: Convex backend started with PID ${backend_pid}"
    echo "INFO: Waiting for backend to be ready..."
    sleep 5

    export CONVEX_SELF_HOSTED_URL="http://127.0.0.1:${port}"
    export CONVEX_SELF_HOSTED_ADMIN_KEY="${admin_key}"

    echo "INFO: Checking if convex npm package is installed..."
    if ! npm ls convex > /dev/null 2>&1; then
        echo "INFO: convex npm package not found. Installing..."
        npm install convex
    else
        echo "INFO: convex npm package is installed."
    fi

    # Default OP_ENV_FILE if not set
    set +eu
    if [ -z "${OP_ENV_FILE:-}" ]; then
        OP_ENV_FILE=".env.local"
    fi
    set -eu 

    # We do NOT pass --env-file here because that forces Convex to look for connection info in the file
    # instead of using our exported CONVEX_SELF_HOSTED_* variables.
    npx convex deploy

    wait
}

main() {
    local instance_name="$1"
    local secret="$2"
    local port="$3"
    local data_folder="$4"

    if [ -z "$instance_name" ] || [ -z "$secret" ] || [ -z "$port" ]; then
        echo "ERROR: Missing required arguments."
        echo "Usage: $0 <instance_name> <secret> <port> [data_folder]"
        echo "  data_folder defaults to ./data if not specified"
        exit 1
    fi

    # Default data folder to ./data if not provided
    if [ -z "$data_folder" ]; then
        data_folder="./data"
    fi

    local proxy_port=$((port + 1))

    print_banner "${instance_name}" "${port}" "${proxy_port}" "${data_folder}"

    run_convex_backend "${instance_name}" "${secret}" "${port}" "${proxy_port}" "${data_folder}"
}

main "$@"
