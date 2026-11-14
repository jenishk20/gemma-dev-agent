require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.touches.track_time = false

  # Configure default environment settings
  config.environment_variable = "development"

  if config.respond_to?(:cache_store)
    config.cache_store = :memory_store
  end

  config.active_storage.service = :local

  config.action_dispatch.show_exceptions_page? = true
end