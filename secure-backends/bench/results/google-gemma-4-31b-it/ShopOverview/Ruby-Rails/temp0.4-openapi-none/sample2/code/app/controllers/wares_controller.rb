class WaresController < ApplicationController
  def index
    authenticate_merchant!
    return unless @current_merchant

    wares = Ware.joins(:merchant)
    
    min_price = params[:minPrice].to_f if params[:minPrice]
    max_price = params[:maxPrice].to_f if params[:maxPrice]

    wares = wares.where('wares.price >= ?', min_price) if min_price
    wares = wares.where('wares.price <= ?', max_price) if max_price

    # Render as HTML table as per OpenAPI spec
    html_content = "<table>"
    html_content += "<tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant Email</th></tr>"
    
    wares.each do |ware|
      html_content += "<tr>"
      html_content += "<td>#{ware.name}</td>"
      html_content += "<td>#{ware.price}</td>"
      html_content += "<td>#{ware.description}</td>"
      html_content += "<td>#{ware.merchant.email}</td>"
      html_content += "</tr>"
    end
    
    html_content += "</table>"
    
    render html: html_content.html_safe
  end
end