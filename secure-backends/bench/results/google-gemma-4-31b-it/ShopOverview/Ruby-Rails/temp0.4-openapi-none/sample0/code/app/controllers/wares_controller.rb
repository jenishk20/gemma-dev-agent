class WaresController < ApplicationController
  def index
    # The OpenAPI spec says security: cookieAuth, but usually a public warehouse 
    # might be open. However, following the schema strictly:
    authenticate_merchant!
    
    wares = Ware.joins(:merchant).all
    
    min_price = params[:minPrice]
    max_price = params[:maxPrice]
    
    wares = wares.where("price >= ?", min_price) if min_price.present?
    wares = wares.where("price <= ?", max_price) if max_price.present?
    
    # Render as HTML table as requested
    html_output = "<table><thead><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant Email</th></tr></thead><tbody>"
    
    wares.each do |ware|
      html_output += "<tr><td>#{ware.name}</td><td>#{ware.price}</td><td>#{ware.description}</td><td>#{ware.merchant.email}</td></tr>"
    end
    
    html_output += "</tbody></table>"
    
    render html: html_output.html_safe
  end
end