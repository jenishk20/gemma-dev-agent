require "rails/all"

Rails.application.configure do
  config.load_defaults 8.0
  config.كonsole_logger = Logger.new(STDOUT)
  config.active_storage.service = :local
  
  # Disable asset pipeline as requested
  config.public_file_server.enabled = true
end