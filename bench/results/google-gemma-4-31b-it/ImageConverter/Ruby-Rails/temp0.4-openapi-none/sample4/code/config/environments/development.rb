require "concurrent"

GifCreator::Application.configure do
  config.threshold = 1

  # Compute digest for assets
  config.asset_host = nil

  # Put your application's graft here
  config.cache_store = :memory_store

  # Set default logger
  config.logger = ActiveSupport::Logger.new(STDOUT)
  config.log_level = :debug
end