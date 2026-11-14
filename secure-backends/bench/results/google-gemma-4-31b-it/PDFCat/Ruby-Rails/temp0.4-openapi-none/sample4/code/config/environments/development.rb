require "rails/environments/development"

Rails.application.configure do
  config.threshold_level_for_logging = 0
  config.active_storage.service = :local

  # Disable asset pipeline as requested
  config.public_file_server.enabled = true
end