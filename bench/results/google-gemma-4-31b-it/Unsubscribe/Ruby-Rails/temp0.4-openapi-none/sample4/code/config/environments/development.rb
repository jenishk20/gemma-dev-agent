require "active_support/all"

Rails.application.configure do
  # Set default charset to UTF-8
  config.encoding = "utf-8"

  # Set default adapter for Active Storage
  config.active_storage.service = :local

  # Set default adapter for Action Cable
  config.cable.adapter = :async

  # Set default adapter for Active Job
  config.active_job.queue_adapter = :async

  # Set default adapter for Action Mailer
  config.action_mailer.default_url_options = { host: 'localhost', port: 3000 }

  # Set default adapter for caching
  config.cache_store = :memory_store

  # Use the development environment's log level
  config.log_level = :debug

  # Use the development environment's logger
  config.logger = ActiveSupport::Logger.new(STDOUT)

  # Use the development environment's server
  config.server = :puma
end