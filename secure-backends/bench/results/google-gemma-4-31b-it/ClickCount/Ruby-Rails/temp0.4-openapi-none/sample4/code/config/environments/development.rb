require "rails/all"

Rails.application.configure do
  # Keep all logger output for debugging
  config.log_level = :debug

  # Use cached expanded paths for all action controllers
  config.action_controller.raise_on_exception = false
  
  # Ensure we don't use asset pipeline as requested
  config.public_file_server.enabled = true
end