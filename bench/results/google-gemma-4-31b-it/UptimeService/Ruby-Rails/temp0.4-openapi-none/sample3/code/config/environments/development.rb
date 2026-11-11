require "active_support/all"

Rails.application.configure do
  # Set default encoding
  config.encoding = "utf-8"

  # Configure application logger
  config.logger = ActiveSupport::Logger.new(STDOUT)

  # Set default adapter for Action Mailer
  config.action_mailer.default_url_options = { host: 'localhost', port: 3000 }

  # Disable caching for development
  config.cache_store = :memory_cache
  config.action_controller.consider_all_requests_local = true
end