class WaresController < ApplicationController
  def index
    # The API spec requires cookieAuth for this endpoint
    authenticate_merchant!
    return unless @current_merchant

    wares = Ware.joins(:merchant).all

    # Filtering
    min_price = params[:minPrice].to_f if params[:minPrice]
    max_price = params[:maxPrice].to_f if params[:maxPrice]

    wares = wares.where('wares.price >= ?', min_price) if min_price
    wares = wares.where('wares.price <= ?', max_price) if max_price

    # Render as HTML table
    html = "<table border='1'><thead><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant Email</th></tr></thead><tbody>"
    
    wares.each do |ware|
      html += "<tr><td>#{ware.name}</td><td>#{ware.price}</td><td>#{ware.description}</td><td>#{ware.merchant.email}</td></tr>"
    end
    
    html += "</tbody></table>"
    
    render html: html.html_safe
  end
end