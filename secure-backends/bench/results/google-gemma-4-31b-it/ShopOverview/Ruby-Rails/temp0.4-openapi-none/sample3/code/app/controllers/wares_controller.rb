class WaresController < ApplicationController
  def index
    # The OpenAPI spec says this endpoint is secured by cookieAuth
    authenticate_merchant!
    return unless @current_merchant

    wares = Ware.joins(:merchant).select('wares.*, merchants.email as merchant_email')

    min_price = params[:minPrice].to_f if params[:minPrice].present?
    max_price = params[:maxPrice].to_f if params[:maxPrice].present?

    wares = wares.where('price >= ?', min_price) if min_price
    wares = wares.where('price <= ?', max_price) if max_price

    html_table = "<table>"
    html_table += "<tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant Email</th></tr>"
    
    wares.each do |ware|
      html_table += "<tr><td>#{ware.name}</td><td>#{ware.price}</td><td>#{ware.description}</td><td>#{ware.merchant_email}</td></tr>"
    end
    html_table += "</table>"

    render html: html_table.html_safe
  end
end