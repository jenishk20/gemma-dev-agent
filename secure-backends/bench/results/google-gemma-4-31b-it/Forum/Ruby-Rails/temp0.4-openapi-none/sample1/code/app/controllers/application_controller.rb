class ApplicationController < ActionController::API
  # We inherit from ActionController::API but we need to support HTML rendering 
  # for the GET /messages endpoint as per the OpenAPI spec.
  include ActionView::Helpers
  include ActionController::ViewInstances
end