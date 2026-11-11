require "active_support/on_load"

Rails.application.configure do
  # Set default environment to development
  config.load_defaults 8.0

  # Use cached expanded paths specified by the Asset Pipeline
  # config.assets.compile = false # Disabled as per instructions

  # Use SQLite for development
  config.active_record.database_sharing_settings = {}
  
  # Allow all hosts for development
  config.hosts.clear
end