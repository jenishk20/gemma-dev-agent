require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.threshold = 500
  config.consider_all_requests_local = true
  config.active_storage.service = :local

  # Set logger
  config.logger = ActiveSupport::Logger.new(STDOUT)
  
  # Disable asset pipeline as requested
  config.public_file_server.enabled = false
end