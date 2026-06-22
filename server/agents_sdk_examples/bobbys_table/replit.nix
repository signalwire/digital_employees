{ pkgs }: {
  # Python itself is provided by the python-3.12 module in .replit.
  # Python packages are installed from requirements.txt by start_replit.sh
  # (pip). Add only SYSTEM-level deps here if a wheel ever needs one.
  deps = [];
}
