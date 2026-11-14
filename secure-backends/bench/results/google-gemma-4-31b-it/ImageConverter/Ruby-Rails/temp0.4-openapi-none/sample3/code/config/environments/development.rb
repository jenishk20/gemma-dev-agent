require "active_support/all"

Rails.application.configure do
  config.threshold = 100

  # Configure database for development
  config.active_storage.service = :local

  config. ActiveRecord.raise_in_transactional_callbacks_after_commit = false
  
  # Disable asset pipeline as requested
  config.public_file_server.enabled = true
end