require "rails/all"

Rails.application.configure do
  # Configure a log level for the environment
  config.log_level = :debug

  # Configure this application to contain the environment's LDAP configuration
  config.active_storage.service = :local

  # Disable assets for API mode
  config.public_file_server.enabled = true
end