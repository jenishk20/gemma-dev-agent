class ApplicationController < ActionController::API
  # We inherit from ActionController::API for the JSON parts, 
  # but we need to include ActionController::Rendering to support HTML responses.
  include ActionController::Rendering
end