#!/usr/bin/env bash
# SKKU contest workspace first-time setup script.
#
# This script is intended for new students setting up this workspace.
# It installs common ROS 2 / Python dependencies, copies Gazebo models,
# builds the workspace, and prints the commands needed for future shells.

if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$SCRIPT_DIR"
ROS_DISTRO="${ROS_DISTRO:-humble}"
ROS_SETUP="/opt/ros/${ROS_DISTRO}/setup.bash"
PYTHON_BIN="/usr/bin/python3"
PIP_CMD=("$PYTHON_BIN" -m pip)

MODE="auto"          # auto|gpu|cpu
SKIP_APT=0
SKIP_PIP=0
SKIP_BUILD=0
VERIFY_ONLY=0

usage() {
  cat <<EOF
Usage: ./install.sh [options]

Recommended:
  ./install.sh --auto

Options:
  --auto         Detect NVIDIA GPU automatically. Default.
  --gpu          Install GPU-oriented Python packages.
  --cpu          Install CPU-oriented Python packages.
  --skip-apt     Skip apt package installation.
  --skip-pip     Skip Python pip package installation.
  --skip-build   Skip colcon build.
  --verify-only  Only check the current environment.
  -h, --help     Show this help.

After setup, open a new terminal or run:
  source ~/.bashrc
  cd "$WORKSPACE_DIR"
  source install/setup.bash
EOF
}

for arg in "$@"; do
  case "$arg" in
    --auto) MODE="auto" ;;
    --gpu) MODE="gpu" ;;
    --cpu) MODE="cpu" ;;
    --skip-apt) SKIP_APT=1 ;;
    --skip-pip) SKIP_PIP=1 ;;
    --skip-build) SKIP_BUILD=1 ;;
    --verify-only) VERIFY_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "[install][ERROR] Unknown option: $arg"
      usage
      exit 1
      ;;
  esac
done

log() { echo "[install] $*"; }
warn() { echo "[install][WARN] $*"; }
die() { echo "[install][ERROR] $*" >&2; exit 1; }

preflight() {
  log "workspace: $WORKSPACE_DIR"
  log "ROS distro: $ROS_DISTRO"

  [[ -d "$WORKSPACE_DIR/src" ]] || die "src/ directory not found. Run this script from the workspace root."
  [[ -x "$PYTHON_BIN" ]] || die "$PYTHON_BIN not found."

  if [[ ! -f "$ROS_SETUP" ]]; then
    die "ROS setup file not found: $ROS_SETUP
Install ROS 2 Humble first, then run this script again."
  fi

  # shellcheck disable=SC1090
  source "$ROS_SETUP"

  command -v ros2 >/dev/null 2>&1 || die "ros2 command not found after sourcing $ROS_SETUP"

  local py_ver
  py_ver="$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [[ "$py_ver" != "3.10" ]]; then
    warn "Expected Python 3.10 for ROS 2 Humble, got $py_ver from $PYTHON_BIN"
  fi
}

detect_mode() {
  if [[ "$MODE" == "auto" ]]; then
    if command -v nvidia-smi >/dev/null 2>&1; then
      MODE="gpu"
    else
      MODE="cpu"
    fi
  fi
  log "Python install mode: $MODE"
}

install_apt_packages() {
  if [[ "$SKIP_APT" -eq 1 ]]; then
    log "Skipping apt packages (--skip-apt)"
    return
  fi

  log "Installing apt packages. sudo password may be required."
  sudo apt-get update
  sudo apt-get install -y \
    build-essential cmake git curl wget \
    python3-pip python3-venv python3-dev python3-colcon-common-extensions \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgtk-3-0 libgomp1 libxcb-xinerama0 \
    gazebo \
    ros-${ROS_DISTRO}-ament-cmake \
    ros-${ROS_DISTRO}-rclpy \
    ros-${ROS_DISTRO}-rosidl-default-generators \
    ros-${ROS_DISTRO}-rosidl-default-runtime \
    ros-${ROS_DISTRO}-std-msgs \
    ros-${ROS_DISTRO}-sensor-msgs \
    ros-${ROS_DISTRO}-geometry-msgs \
    ros-${ROS_DISTRO}-nav-msgs \
    ros-${ROS_DISTRO}-visualization-msgs \
    ros-${ROS_DISTRO}-cv-bridge \
    ros-${ROS_DISTRO}-message-filters \
    ros-${ROS_DISTRO}-tf2-ros \
    ros-${ROS_DISTRO}-tf2-py \
    ros-${ROS_DISTRO}-rviz2 \
    ros-${ROS_DISTRO}-xacro \
    ros-${ROS_DISTRO}-image-transport \
    ros-${ROS_DISTRO}-gazebo-ros-pkgs \
    ros-${ROS_DISTRO}-gazebo-ros \
    ros-${ROS_DISTRO}-gazebo-msgs \
    ros-${ROS_DISTRO}-gazebo-plugins \
    ros-${ROS_DISTRO}-gazebo-ros2-control \
    ros-${ROS_DISTRO}-ros2-control \
    ros-${ROS_DISTRO}-ros2-controllers \
    ros-${ROS_DISTRO}-controller-manager \
    ros-${ROS_DISTRO}-joint-state-broadcaster \
    ros-${ROS_DISTRO}-position-controllers \
    ros-${ROS_DISTRO}-velocity-controllers \
    ros-${ROS_DISTRO}-joint-state-publisher \
    ros-${ROS_DISTRO}-joint-state-publisher-gui \
    ros-${ROS_DISTRO}-robot-state-publisher \
    ros-${ROS_DISTRO}-ackermann-msgs
}

install_python_packages() {
  if [[ "$SKIP_PIP" -eq 1 ]]; then
    log "Skipping Python packages (--skip-pip)"
    return
  fi

  log "Installing Python packages with $PYTHON_BIN --user"
  "${PIP_CMD[@]}" install --user --upgrade pip wheel

  # ROS 2 Humble's Python package tooling is most stable with setuptools 58.x.
  "${PIP_CMD[@]}" install --user "setuptools==58.2.0"

  if [[ "$MODE" == "cpu" ]]; then
    "${PIP_CMD[@]}" install --user --index-url https://download.pytorch.org/whl/cpu \
      "torch" "torchvision"
  else
    "${PIP_CMD[@]}" install --user "torch" "torchvision"
  fi

  "${PIP_CMD[@]}" install --user \
    "numpy<2.0" \
    "opencv-python" \
    "pyserial" \
    "pynput" \
    "ultralytics" \
    "transforms3d"
}

sync_gazebo_models() {
  local source_models_dir="$WORKSPACE_DIR/src/simulation_pkg/models"
  local models_dir="$HOME/.gazebo/models"

  if [[ ! -d "$source_models_dir" ]]; then
    warn "Gazebo model directory not found: $source_models_dir"
    return
  fi

  log "Copying Gazebo models to $models_dir"
  mkdir -p "$models_dir"
  cp -r "$source_models_dir"/* "$models_dir"/
}

ensure_bashrc_block() {
  local bashrc_file="$HOME/.bashrc"
  local begin="# >>> SKKU_CONTEST_ENV >>>"

  if grep -Fq "$begin" "$bashrc_file"; then
    log "~/.bashrc already contains SKKU contest helper block"
    return
  fi

  log "Adding helper aliases and environment variables to ~/.bashrc"
  cat >> "$bashrc_file" <<EOF

# >>> SKKU_CONTEST_ENV >>>
alias humble='source $ROS_SETUP && echo "ros2 $ROS_DISTRO activated"'
alias skku_ws='cd "$WORKSPACE_DIR"'
alias skku_build='cd "$WORKSPACE_DIR" && colcon build --symlink-install'
alias skku_source='source "$WORKSPACE_DIR/install/setup.bash"'

if command -v nvidia-smi >/dev/null 2>&1; then
  export SKKU_YOLO_DEVICE="\${SKKU_YOLO_DEVICE:-cuda:0}"
else
  export SKKU_YOLO_DEVICE="\${SKKU_YOLO_DEVICE:-cpu}"
fi

export SKKU_COMPACT_LOGS="\${SKKU_COMPACT_LOGS:-1}"
# <<< SKKU_CONTEST_ENV <<<
EOF
}

build_workspace() {
  if [[ "$SKIP_BUILD" -eq 1 ]]; then
    log "Skipping colcon build (--skip-build)"
    return
  fi

  log "Building workspace"
  cd "$WORKSPACE_DIR"
  # shellcheck disable=SC1090
  source "$ROS_SETUP"
  colcon build --symlink-install
}

verify_env() {
  log "Verifying ROS packages and Python modules"

  # shellcheck disable=SC1090
  source "$ROS_SETUP"

  if [[ -f "$WORKSPACE_DIR/install/setup.bash" ]]; then
    # shellcheck disable=SC1091
    source "$WORKSPACE_DIR/install/setup.bash"
  fi

  "$PYTHON_BIN" - <<'PY'
import importlib

for name in ["numpy", "cv2", "serial"]:
    module = importlib.import_module(name)
    print(f"[verify] {name}: {getattr(module, '__version__', 'OK')}")

try:
    torch = importlib.import_module("torch")
    print(f"[verify] torch: {torch.__version__}")
    print(f"[verify] torch.cuda.is_available: {torch.cuda.is_available()}")
except Exception as e:
    print(f"[verify][WARN] torch import failed: {e}")

try:
    ultralytics = importlib.import_module("ultralytics")
    print(f"[verify] ultralytics: {getattr(ultralytics, '__version__', 'OK')}")
except Exception as e:
    print(f"[verify][WARN] ultralytics import failed: {e}")
PY

  if [[ -f "$WORKSPACE_DIR/install/setup.bash" ]]; then
    ros2 pkg list | grep -q '^camera_pkg$' && log "ok: camera_pkg found"
    ros2 pkg list | grep -q '^launch_pkg$' && log "ok: launch_pkg found"
  else
    warn "install/setup.bash not found yet. Build was probably skipped."
  fi
}

print_next_steps() {
  cat <<EOF

[install] Setup finished.

Open a new terminal, then run:
  cd "$WORKSPACE_DIR"
  source /opt/ros/$ROS_DISTRO/setup.bash
  source install/setup.bash

Quick test:
  ros2 launch launch_pkg general.py

Useful aliases added to ~/.bashrc:
  humble       source ROS 2
  skku_ws      move to this workspace
  skku_build   build this workspace
  skku_source  source this workspace

EOF
}

main() {
  preflight
  detect_mode

  if [[ "$VERIFY_ONLY" -eq 1 ]]; then
    verify_env
    exit 0
  fi

  install_apt_packages
  install_python_packages
  sync_gazebo_models
  ensure_bashrc_block
  build_workspace
  verify_env
  print_next_steps
}

main "$@"
