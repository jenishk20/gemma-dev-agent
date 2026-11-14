require "active_support/core_ext/slogging"

Rails.application.configure do
  config.threshold = 100
  config.cache = SolidCache::Store
  config.active_job.queue_adapter = :solid_queue

  config.development_mode = true
  config.telemetry.enabled = true

  config.log_level = :debug
  config.log_formatter = :color

  config.active_storage.service = :local

  config.autoload_timeout = 5
end