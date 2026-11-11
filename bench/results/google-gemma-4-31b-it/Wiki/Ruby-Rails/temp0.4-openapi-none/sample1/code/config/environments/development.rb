require "rails/all"

Rails.application.configure do
  # Use the standard development configuration
  config.load_defaults 8.0

  # Disable assets pipeline as requested
  config.public_file_server.enabled = true
  
  # Allow the app to be accessed from outside the container
  config.hosts.clear
end