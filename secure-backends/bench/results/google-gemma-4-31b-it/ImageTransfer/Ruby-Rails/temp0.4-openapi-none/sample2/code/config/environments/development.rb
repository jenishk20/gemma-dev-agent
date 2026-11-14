require "active_support/all"

Rails.application.configure do
  config.threshold_level = :log
  config.logger = ActiveSupport::Logger.new(STDOUT)
  config.time_zone = "UTC"
  config.x_sendfile.enabled = false

  # Disable caching for development
  config.action_controller.consider_in_line_cache = false
  config.active_storage.service = :local
  
  config.active_record.migration_s = "0"
end