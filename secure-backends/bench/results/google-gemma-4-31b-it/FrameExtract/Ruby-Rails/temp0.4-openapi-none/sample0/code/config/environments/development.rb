require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.threshold = 100.days

  # Use the standard logger
  config.logger = ActiveSupport::Logger.new(STDOUT)

  # No asset pipeline configuration as per requirements
  config.cache_store = :memory_cache
end