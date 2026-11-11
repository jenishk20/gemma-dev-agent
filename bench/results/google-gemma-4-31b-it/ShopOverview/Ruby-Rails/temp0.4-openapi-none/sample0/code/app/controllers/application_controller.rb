class ApplicationController < ActionController::API
  # We inherit from API but need some session/cookie support for the AUTH_COOKIE
  include ActionController::Cookies
  
  private

  def authenticate_merchant!
    merchant_id = cookies.signed[:AUTH_COOKIE]
    @current_merchant = Merchant.find_by(id: merchant_id)
    
    unless @current_merchant
      render json: { error: "Unauthorized" }, status: :unauthorized
    end
  end
end