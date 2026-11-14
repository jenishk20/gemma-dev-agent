class ApplicationController < ActionController::API
  def current_merchant
    @current_merchant ||= Merchant.find_by(id: cookies.signed[:merchant_id])
  end

  def authenticate_merchant!
    unless current_merchant
      render json: { error: 'Unauthorized' }, status: :unauthorized
    end
  end
end